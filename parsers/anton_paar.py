# -*- coding: utf-8 -*-
"""Parse Anton Paar (Quantachrome Autosorb 6300 XR) output files."""
# pylint: disable-msg=invalid-name # to allow non-conforming variable names
import re

import dateutil.parser
import numpy as np
import pandas as pd

# 字段映射 - 对应 Autosorb 6300 XR 格式
# 注意: 键名需要与 makeAIF 函数期望的键名一致
_FIELDS = {
    'material': {
        'text': ['sample id'],
        'name': 'material',  # 对应 makeAIF 中的 data_meta['material']
    },
    'adsorbate': {
        'text': ['analysis gas'],
        'name': 'adsorbate',
    },
    'temperature': {
        'text': ['analysis temp'],
        'name': 'temperature',
    },
    'operator': {
        'text': ['operator'],
        'name': 'operator',
    },
    'apparatus': {
        'text': ['instrument'],
        'name': 'apparatus',
    },
    'mass': {
        'text': ['sample weight'],
        'name': 'material_mass',  # 对应 makeAIF 中的 data_meta['material_mass']
    },
    'date': {
        'text': ['analysis date'],
        'name': 'date',
    },
    'sample_description': {
        'text': ['description'],
        'name': 'sample_description',
    },
    'comment': {
        'text': ['comments'],
        'name': 'comment',
    },
    'duration': {
        'text': ['duration'],
        'name': 'analysis_time',
    },
    'void_volume_cold': {
        'text': ['void vol. (cold)'],
        'name': 'void_volume_cold',
    },
    'void_volume_warm': {
        'text': ['void vol. (warm)'],
        'name': 'void_volume_warm',
    },
    'nonideality_cold': {
        'text': ['non-ideality factor (cold)'],
        'name': 'nonideality_cold',
    },
    'nonideality_warm': {
        'text': ['non-ideality factor (warm)'],
        'name': 'nonideality_warm',
    },
    'isotherm_data': {
        'pressure': 'pressure',
        'p0': 'pressure_saturation',
        'relative_pressure': 'pressure_relative',
        'volume_stp': 'loading',
        'volume_stp_g': 'loading_mass',
        'time': 'measurement_time',
    }
}


def parse(path):
    """
    Get the isotherm and sample data from an Anton Paar (Autosorb 6300 XR) file.

    Parameters
    ----------
    path : str
        Path to the file to be read.

    Returns
    -------
    tuple
        (material_info, adsorption_data, desorption_data)
    """
    # pylint: disable-msg=too-many-locals
    # pylint: disable-msg=too-many-branches
    # pylint: disable-msg=too-many-statements

    # load datafile
    with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
        lines = fp.readlines()

    # get experimental and material parameters
    material_info = {}
    columns = []
    raw_data = []

    # 记录数据开始行
    ads_start = None

    for index, line in enumerate(lines):
        original_line = line

        # 跳过空行和分隔线
        if not line.strip() or line.strip().startswith('-'):
            continue

        # 转换为小写进行匹配
        line_lower = line.lower().strip()

        # 查找数据列标题 - 包含 "Pressure" 和 "p₀"
        if ads_start is None and 'pressure' in line_lower and 'p₀' in line_lower:
            ads_start = index + 2  # 数据从下两行开始
            continue

        # 解析元数据键值对
        # 格式: "Key  Value" (多个空格分隔)
        if ads_start is None:
            # 尝试匹配 "Key  Value" 格式
            # 格式: "      Sample ID  EL1-112" (左侧有空格，键名后跟两个或以上空格)
            match = re.match(r'^\s*([A-Za-z][A-Za-z0-9\s\-\._]*)(\s{2,})(.+)$', original_line)
            if match:
                key = match.group(1).strip()
                value = match.group(3).strip()

                # 查找匹配的字段
                for field_key, field_info in _FIELDS.items():
                    if field_key == 'isotherm_data':
                        continue
                    for text in field_info.get('text', []):
                        if text.lower() == key.lower():
                            name = field_info.get('name')
                            material_info[name] = value
                            break

    # 解析数据部分
    if ads_start is None:
        raise ValueError("Could not find data section in file")

    # 获取列标题
    col_line = lines[ads_start - 2].strip() if ads_start >= 2 else ""
    units_line = lines[ads_start - 1].strip() if ads_start >= 1 else ""

    # 解析列名
    columns = []
    for col in re.split(r'\s{2,}', col_line):
        col = col.strip()
        if col:
            columns.append(col)

    # 解析单位
    units = re.split(r'\s{2,}', units_line)

    # 设置压力单位
    if units and 'torr' in units[0].lower():
        material_info['pressure_unit'] = 'Torr'

    # 设置加载单位
    if len(units) >= 3 and 'cm³' in units[2].lower():
        material_info['loading_unit'] = 'cm³ STP'

    # 解析数据行
    for index, line in enumerate(lines):
        if index < ads_start:
            continue

        line = line.strip()
        if not line:
            continue

        # 跳过分隔符行
        if line.startswith('-'):
            continue

        # 解析数据
        try:
            values = line.split()
            if len(values) >= 5:
                # 提取数值部分
                numeric_values = []
                for v in values:
                    try:
                        numeric_values.append(float(v))
                    except ValueError:
                        break
                if len(numeric_values) >= 4:
                    raw_data.append(numeric_values[:6])  # 最多6列
        except Exception:
            continue

    if not raw_data:
        raise ValueError("No data found in file")

    # 创建 DataFrame
    # 列: Pressure, p0, Relative Pressure, Amount Adsorbed (cm³ STP), Amount Adsorbed (cm³ STP/g), Time
    data = np.array(raw_data, dtype=float)

    # 确保列名正确对应
    col_names = ['pressure', 'pressure_saturation', 'pressure_relative',
                 'loading', 'loading_mass', 'measurement_time']

    if data.shape[1] >= len(col_names):
        df = pd.DataFrame(data[:, :len(col_names)], columns=col_names[:data.shape[1]])
    else:
        # 如果数据列数不足，使用默认列名
        df = pd.DataFrame(data, columns=col_names[:data.shape[1]])

    # 处理质量单位
    if 'material_mass' in material_info:
        mass_str = material_info['material_mass']
        # 格式: "0.045100 g"
        mass_match = re.match(r'([\d.]+)\s*([a-zA-Z]+)', mass_str)
        if mass_match:
            material_info['material_mass'] = float(mass_match.group(1))
            material_info['material_unit'] = mass_match.group(2)

    # 处理温度
    if 'temperature' in material_info:
        temp_str = material_info['temperature']
        # 格式: "77.35 K"
        temp_match = re.match(r'([\d.]+)\s*([a-zA-Z]+)', temp_str)
        if temp_match:
            material_info['temperature'] = float(temp_match.group(1))
            material_info['temperature_unit'] = temp_match.group(2)

    # 处理日期
    if 'date' in material_info:
        try:
            material_info['date'] = dateutil.parser.parse(
                material_info['date']).isoformat()
        except Exception:
            pass

    # 设置默认单位
    if 'pressure_unit' not in material_info:
        material_info['pressure_unit'] = 'Torr'
    if 'loading_unit' not in material_info:
        material_info['loading_unit'] = 'cm³ STP'
    if 'material_unit' not in material_info:
        material_info['material_unit'] = 'g'

    # 分离吸附和脱附分支
    # 寻找压力最大点（转折点）
    turning_point = df['pressure'].argmax() + 1

    return (material_info, df[:turning_point], df[turning_point:])
