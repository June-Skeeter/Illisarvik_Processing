
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd

from shapely.geometry import Point, Polygon, MultiPolygon, shape

import rasterio
from rasterio import features
from rasterio.transform import from_origin
from rasterio.plot import show

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
		with rasterio.open(Domain,'r') as self.Domain:
			self.raster_params = self.Domain.profile
			del self.raster_params['transform']    ### Transfrorms will become irelivant in rio 1.0 - gets rid of future warning
			self.Image = self.Domain.read(1)
		self.fp_params={'dx':dx,'nx':nx,'rs':rs}
		self.Prog = prb.ProgressBar(self.Runs)
		self.Intersections = self.Data[['datetime']].copy()
		for name in self.Classes['Name']:
			self.Intersections[name]=0.0
		self.Intersections['Uplands'] = 0.0
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
				out.write(self.fpf,1)
		self.Sum/=i+1
		Contours(self.out_dir,Sum = self.Sum,raster_params=self.raster_params)
		# with rasterio.open(self.out_dir+'Climatology.tif','w',**self.raster_params) as out:
		# 	out.write(self.Sum,1)

	def intersect(self):
		Sum = 0
		for code in self.Classes['Code']:
			Template = self.Image*0
			Template[self.Image == code] = 1
			Template*= self.fpf
			Contribution = Template.sum()
			Name = self.Classes['Name'].loc[self.Classes['Code'] == code].values[0]
			self.Intersections.ix[self.i,Name] = Contribution
			Sum+=Contribution
		self.Intersections.ix[self.i,'Uplands'] = 1.0 - Sum

class Contours(object):
	"""docstring for ClassName"""
	def __init__(self,RasterPath,Sum=None,raster_params=None,Jobs=None,r=[.25,.50,.70,.80,.90],ax=None):
		super(Contours, self).__init__()
		self.RasterPath=RasterPath
		self.raster_params=raster_params
		self.r = r
		self.ax=ax
		if Sum is not None:
			self.Sum = Sum
			self.job = 'Climatology'
			self.Write_Contour()
		elif Jobs is not None:
			self.Jobs = Jobs
			self.Sum()

	def Sum(self):		
		for job in self.Jobs:
			self.job = job
			nj = 0		
			print(self.job+':')
			self.Prog = prb.ProgressBar(self.Jobs[job].shape[0])
			for date in self.Jobs[job]:
				self.Prog.Update(nj)
				Name = str(date).replace(' ','_').replace('-','').replace(':','')
				my_file = Path("/path/to/file")
				try:
					with rasterio.open(self.RasterPath+'30min/'+Name+'.tif','r') as FP:
						self.raster_params = FP.profile
						del self.raster_params['transform']    ### Transfrorms will become irelivant in rio 1.0 - gets rid of future warning
						Image = FP.read(1)
						if nj == 0:
							self.Sum = Image
						else:
							self.Sum += Image
						nj+=1
				except:
					pass
			self.Sum/=nj
			self.Write_Contour()

	def Write_Contour(self):
		with rasterio.open(self.RasterPath+self.job+'.tiff','w',**self.raster_params) as out:
			out.write(self.Sum,1)
			transform=out.transform

		Copy = self.Sum.copy()

		FlatCopy = np.sort(Copy.ravel())[::-1]
		Cumsum = np.sort(Copy.ravel())[::-1].cumsum()

		dx = self.raster_params['affine'][0]
		d = {}
		d['contour'] = []
		geometry = list()
		for r in self.r:
			pct = FlatCopy[np.where(Cumsum < r)]
			Mask = self.Sum.copy()
			Mask[Mask>=pct[-1]] = 1
			Mask[Mask<pct[-1]] = np.nan
			# plt.figure()
			# plt.imshow(Mask)
			multipart = 'No'
			for shp, val in features.shapes(Mask.astype('int16'), transform=transform):
				if val == 1:
					d['contour'].append(r)
					Poly = shape(shp)
					Poly = Poly.buffer(dx, join_style=1).buffer(-dx, join_style=1)
					Poly = Poly.buffer(-dx, join_style=1).buffer(dx, join_style=1)
					if multipart == 'No':
						geometry.append(Poly)
					else:
						Multi = []
						for part in geometry[-1]:
							Multi.append(part)
						Multi.append(Poly)
						geometry[-1]=MulitPolygon(Multi)
					mulitpart = 'Yes'
		df = pd.DataFrame(data=d)

		geo_df = gpd.GeoDataFrame(df,crs={'init': 'EPSG:32608'},geometry = geometry)
		geo_df['area'] =  geo_df.area 
		geo_df.to_file(self.RasterPath+'Contours/'+self.job+'.shp', driver = 'ESRI Shapefile')
		if self.ax is not None:
			geo_df.plot(facecolor='None',edgecolor='black',ax=self.ax)

		