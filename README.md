# Adsorption Information File
This repository contains the details of an universal file format for gas adsorption experiments.

## Core dictionary
The current dictionary of data items used by adsorption information files can be found in:
[aifdictionary.json](/aifdictionary.json)
Feel free to initate a pull request to add new terms.

## raw2aif converter
A simple program was produced to facilitate the production of adsorption information files from raw analysis text files exported by Quantachrome software (*.txt*), Belsorp software raw data files (*.DAT*), xls files exported by Micromeritics software (*.xls*), and Anton Paar Autosorb instruments (*.txt*).

[adsorptioninformationformat.com/raw2aif](http://adsorptioninformationformat.com/raw2aif)

The steps to using this program is straightforward and a short tutorial can be found [here](https://youtu.be/uNojsNWJDCA).

## New Features (Forked Version)

This forked version adds the following enhancements:

### Anton Paar Autosorb Support
- Added support for Anton Paar Autosorb 6300 XR data files
- Auto-detection of file type (Anton Paar vs Quantachrome)
- Outputs amount adsorbed in cm³ STP/g (per gram) units

### Web Interface
- Built-in Flask web application for easy file conversion
- Automatic plot generation of adsorption isotherms
- Drag-and-drop file upload
- Supports all original file formats

### Docker Deployment
- Easy deployment via Docker container
```bash
# Build
docker build -t aif-converter .

# Run
docker run -d -p 5000:5000 --name aif-web aif-converter
```

Then open http://localhost:5000 in your browser.

## Citation
Jack D. Evans, Volodymyr Bon, Irena Senkovska, and Stefan Kaskel, *Langmuir*, **2021**.
[10.1021/acs.langmuir.1c00122](https://dx.doi.org/10.1021/acs.langmuir.1c00122)
