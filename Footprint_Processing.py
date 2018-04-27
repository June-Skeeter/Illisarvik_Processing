
import sys

import numpy as np
import pandas as pd
import geopandas as gpd

from shapely.geometry import Point, Polygon, MultiPolygon, shape

import rasterio
from rasterio import features
from rasterio.transform import from_origin
from matplotlib import pyplot as plt

from datetime import datetime

from functools import partial
from multiprocessing import Pool

import ProgressBar as prb

from Klujn_2015_FootprinModel.calc_footprint_FFP_climatology_SkeeterEdits import FFP_climatology

class Calculate(object):
	"""docstring for Calculate"""
	def __init__(self,Data,Domain,XY,nx=1000,dx=1,rs=[50,75,90]):
		super(Calculate, self).__init__()
		print(Data)
		self.Runs = Data.shape[0]
		self.Data = Data
		self.Domain = rasterio.open(Domain,'r')
		self.Image = self.Domain.read(1)
		self.Template = self.Image*0
		self.fp_params={'dx':dx,'nx':nx,'rs':rs}
		self.Prog = prb.ProgressBar(self.Runs)
		plt.imshow(self.Image)

		self.run()

	def run(self):
		for i in range(self.Runs):
			Name = str(self.Data['datetime'].iloc[i]).replace(' ','_').replace('-','').replace(':','')
			self.Prog.Update(i)
