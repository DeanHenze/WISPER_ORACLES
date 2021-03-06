# WISPER ORACLES data products 
## data products, processing code, calibration information

Data products from the Water Isotope System for Precipitation and Entrainment Research 
(WISPER) during the ORACLES campaign. WISPER is designed to provide in-situ aircraft 
meausrements of atmospheric water concentration and its heavy isotope ratios D/H and 
18O/16O for both total water and cloud water concentrations. A detailed review of the 
instrument, measurements, data products, and calibration procedure can be found in 
[Henze et al., 2022](https://doi.org/10.5194/essd-14-1811-2022). The paper is also included 
in this directory (```essd-14-1811-2022.pdf```).

ORACLES (ObseRvations of Aerosols above CLouds and their intEractionS) is a NASA earth 
science field experiment with three Intensive Observation Periods (IOPs) designed to study 
key processes that determine the climate impacts of African biomass burning aerosols. 
More information on the ORACLES field experiment can be found on the 
[NASA ESPO website](https://espo.nasa.gov/oracles/content/ORACLES) and in 
[Redemann et al., 2021](https://doi.org/10.5194/acp-21-1507-2021).

The WISPER data products provided are:
* 1 Hz time series (```./apply_cal+QC/WISPER_calibrated_data/```).
* Mean latitude-altitude curtains, providing a climatology for each IOP 
  (```./level3_products/```).
* Individual vertical profiles averaged to 50 m altitude bins
  (```./level3_products/```).

This directory contains Python scripts to generate the data products. Calibrated 
1 Hz time series files can be produced by running ```./apply_cal+QC/run_fullcal.py```. The 
script takes raw data from ```./apply_cal+QC/WISPER_raw_data/``` and outputs calibrated 
files to ```./apply_cal+QC/WISPER_calibrated_data/```.

Example usage and expected output... 