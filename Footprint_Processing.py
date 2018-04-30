
import sys

import numpy as np
import pandas as pd
import geopandas as gpd

from shapely.geometry import Point, Polygon, MultiPolygon, shape

import rasterio
from rasterio import features
from rasterio.transform import from_origin

from matplotlib import pyplot as plt
from matplotlib.colors import Normalize

from datetime import datetime

from functools import partial
from multiprocessing import Pool

import ProgressBar as prb

from Klujn_2015_FootprinModel.calc_footprint_FFP_climatology_SkeeterEdits import FFP_climatology

class Calculate(object):
	"""docstring for Calculate"""
	def __init__(self,out_dir,Data,Domain,XY,Classes=None,nx=1000,dx=1,rs=[50,75,90]):
		super(Calculate, self).__init__()
		self.Classes=Classes
		self.out_dir=out_dir
		self.Runs = Data.shape[0]
		self.Data = Data
		self.Domain = rasterio.open(Domain,'r')
		self.raster_params = self.Domain.profile
		del self.raster_params['transform']    ### Transfrorms will become irelivant in rio 1.0 - gets rid of future warning
		self.Image = self.Domain.read(1)
		self.fp_params={'dx':dx,'nx':nx,'rs':rs}
		self.Prog = prb.ProgressBar(self.Runs)
		for name in self.Classes['Name']:
			self.Data[name]=0
		self.Data['Uplands'] = 0
		self.run()

	def run(self):
		for i in range(self.Runs):
			self.i=i
			Name = str(self.Data['datetime'].iloc[i]).replace(' ','_').replace('-','').replace(':','')
			FP = FFP_climatology(zm=[self.Data['Zm'].iloc[i]],z0=[self.Data['Zo'].iloc[i]],h=[self.Data['PBLH'].iloc[i]],ol=[self.Data['L'].iloc[i]],
				sigmav=[self.Data['v_var'].iloc[i]],ustar=[self.Data['u*'].iloc[i]],wind_dir=[self.Data['wind_dir'].iloc[i]],**self.fp_params,)
			self.fpf = np.flipud(FP['fclim_2d'])*self.fp_params['dx']**2
			self.fpf /= self.fpf.sum()    ## Normalize by the domain!
			if self.Classes is not None:
				self.intersect()
			if i == 0:
				self.Sum = self.fpf
			else:
				self.Sum+= self.fpf
			self.Prog.Update(i)
			with rasterio.open(self.out_dir+'30min/'+str(Name)+'.tif','w',**self.raster_params) as out:
				out.write(self.Sum,1)
		self.Sum/=i+1
		with rasterio.open(self.out_dir+'Climatology.tif','w',**self.raster_params) as out:
			out.write(self.Sum,1)
		return(self.Data)

	def intersect(self):
		Sum = 0
		for code in self.Classes['Code']:
			Template = self.Image*0
			Template[self.Image == code] = 1
			Template*= self.fpf
			Contribution = Template.sum()
			Name = self.Classes['Name'].loc[self.Classes['Code'] == code].values[0]
			self.Data.ix[self.i,Name] = Contribution
		self.Data.ix[self.i,Name] = 1- Sum