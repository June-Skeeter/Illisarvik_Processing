
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
	def __init__(self,Data,Domain,XY,Classes=None,nx=1000,dx=1,rs=[50,75,90]):
		super(Calculate, self).__init__()
		self.Classes=Classes
		self.Runs = Data.shape[0]
		self.Data = Data
		self.Domain = rasterio.open(Domain,'r')
		self.Image = self.Domain.read(1)
		self.fp_params={'dx':dx,'nx':nx,'rs':rs}
		self.Prog = prb.ProgressBar(self.Runs)
		for code in self.Classes['Code']:
			self.Data[self.Classes['Name'].loc[self.Classes['Code'] == i]]=0
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
			self.Prog.Update(i)

	def intersect(self):
		Sum = 0
		for code in self.Classes['Code']:
			Template = self.Image*0
			Template[self.Image == code] = 1
			Template*= self.fpf
			Contribution = Template.sum()
			self.Data[self.Classes['Name'].loc[self.Classes['Code'] == code].iloc[self.i] = Contribution
			Sum += Contribution
		self.Data['Uplands'].iloc[self.i] = 1- Sum
		print(self.Data['Uplands'].iloc[self.i])