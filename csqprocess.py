import sys
import os
from csplitb import CSplitB
import ffmpeg
import exiftool
import cv2
import numpy as np
import pickle
import json
from enum import IntEnum

# https://www.eevblog.com/forum/thermal-imaging/csq-file-format/

'''
parser = argparse.ArgumentParser(description="csplitb - Context splitter on binary data.")
parser.add_argument("spliton", help="Hexadecimal representation of data to split on.")
parser.add_argument("infile", help="Input file.")
parser.add_argument("-n", "--number", type=int, help="Number of zeroes to pad filename. Default is 2", default=2)
parser.add_argument("-f", "--prefix", help="Output file prefix. Default is xx", default="xx")
parser.add_argument("-s", "--suffix", help="Output file suffix. Defaults is .dat", default=".dat")
args = parser.parse_args(argv[1:])

csplitb = CSplitB(args.spliton, args.infile, args.number, args.prefix, args.suffix)
return csplitb.run()
'''
# --prefix frame --suffix .fff --number 6  thermalvid.csq
'''
fff splits based on: "46 46 46 00"
fcf splits based on: "46 46 46 00 43 41 50"
seq splits based on: "46 46 46 00 43 41 4D"
csq splits based on: "46 46 46 00 52 54 50"
'''



exifdata = None # exif will be here later

def kelvin(vals):
	""" A property method that returns the thermogram's temperature in
	kelvin (K).
	
	Returns
	-------
	Array[np.float64, ..., ...]
		A 2D array of numpy float values in kelvin. Order is [H, W].
	"""

	# this bit ported from flir.php
	'''
	
    $tmp=explode(" ",$exif[0]['ReflectedApparentTemperature']);
    $Temp_ref = $tmp[0];
    
    $Emissivity=$exif[0]['Emissivity'];
	
	// save Flir values for Plancks Law for better reading in short variables
	$R1=$exif[0]['PlanckR1'];
	$R2=$exif[0]['PlanckR2'];
	$B= $exif[0]['PlanckB'];
	$O= $exif[0]['PlanckO'];
	$F= $exif[0]['PlanckF'];

	print('Plancks values: '.$R1.' '.$R2.' '.$B.' '.$O.' '.$F."\n\n");

	// get displayed temp range in RAW values
	$RAWmax=$exif[0]['RawValueMedian']+$exif[0]['RawValueRange']/2;
	$RAWmin=$RAWmax-$exif[0]['RawValueRange'];

	print('RAW Temp Range from sensor : '.exec($convert.' raw.png -format "%[min] %[max]" info:')."\n");
	printf("RAW Temp Range FLIR setting: %d %d\n",$RAWmin,$RAWmax);

	//overwrite with settings
	if (isset($options['rmin'])) $RAWmin=$options['rmin'];
	if (isset($options['rmax'])) $RAWmax=$options['rmax'];

	printf("RAW Temp Range select      : %d %d\n",$RAWmin,$RAWmax);

	// calc amount of radiance of reflected objects ( Emissivity < 1 )
	$RAWrefl=$R1/($R2*(exp($B/($Temp_ref+273.15))-$F))-$O;
	printf("RAW reflected: %d\n",$RAWrefl); 

	// get displayed object temp max/min and convert to "%.1f" for printing
	$RAWmaxobj=($RAWmax-(1-$Emissivity)*$RAWrefl)/$Emissivity;
	$RAWminobj=($RAWmin-(1-$Emissivity)*$RAWrefl)/$Emissivity;
	$Temp_min=sprintf("%.1f", $B/log($R1/($R2*($RAWminobj+$O))+$F)-273.15);
	$Temp_max=sprintf("%.1f", $B/log($R1/($R2*($RAWmaxobj+$O))+$F)-273.15);
	
	
	----
	// convert every RAW-16-Bit Pixel with Planck's Law to a Temperature Grayscale value and append temp scale
	$Smax=$B/log($R1/($R2*($RAWmax+$O))+$F);
	$Smin=$B/log($R1/($R2*($RAWmin+$O))+$F);
	$Sdelta=$Smax-$Smin;
	exec($convert." raw.png -fx \"($B/ln($R1/($R2*(65535*u+$O))+$F)-$Smin)/$Sdelta\" ir.png");
	'''

	#print(exifdata)
	#Temp_ref = exifdata['ReflectedApparentTemperature'].split(' ')[0]

	#Emissivity = exifdata['Emissivity']

	PlanckR1=exifdata['PlanckR1']
	PlanckR2=exifdata['PlanckR2']
	PlanckB= exifdata['PlanckB']
	PlanckO= exifdata['PlanckO']
	PlanckF= exifdata['PlanckF']

	#print('Plancks values: '+str(PlanckR1)+' '+str(PlanckR2)+' '+str(PlanckB)+' '+str(PlanckO)+' '+str(PlanckF))
	'''
	# get displayed temp range in RAW values
	RawValueMedian=exifdata['RawValueMedian']
	RawValueRange=exifdata['RawValueRange']

	RAWmax=RawValueMedian+RawValueRange/2.0
	RAWmin=RAWmax-RawValueRange

	print("RAW Temp Range FLIR setting: "+str(RAWmin)+" - "+str(RAWmax))

	# calc amount of radiance of reflected objects ( Emissivity < 1 )
	#RAWrefl=PlanckR1/(PlanckR2*(exp(PlanckB/(Temp_ref+273.15))-PlanckF))-PlanckO
	#printf("RAW reflected: "+RAWrefl)

	# convert every RAW-16-Bit Pixel with Planck's Law to a Temperature Grayscale value and append temp scale
	Smax=PlanckB/np.log(PlanckR1/(PlanckR2*(RAWmax+PlanckO))+PlanckF)
	Smin=PlanckB/np.log(PlanckR1/(PlanckR2*(RAWmin+PlanckO))+PlanckF)
	Sdelta=Smax-Smin

	#print(vals[0])

	# ( PlanckB / ln( PlanckR1 / ( PlanckR2 * ( 65535 * u + PlanckO ) ) + PlanckF ) - Smin ) / Sdelta
	# vals=[
	# 	(( PlanckB / np.log( PlanckR1 / ( PlanckR2 * ( 65535 * u + PlanckO ) ) + PlanckF ) - Smin ) / Sdelta)
	# 	for u
	# 	in vals
	# ]
	for i in range(len(vals)):
		# vals[i]=(( PlanckB / np.log( PlanckR1 / ( PlanckR2 * ( 65535 * vals[i] + PlanckO ) ) + PlanckF ) - Smin ) / Sdelta)
		vals[i]=(( PlanckB / np.log( PlanckR1 / ( PlanckR2 * ( 65535.0 * vals[i] + PlanckO ) ) + PlanckF ) - Smin ) / Sdelta)
	'''
	for i in range(len(vals)):
		vals[i]=PlanckB / np.log((PlanckR1 / PlanckR2)*(1. / (vals[i] + PlanckO)) + PlanckF)

	return vals

def celsius(vals):
	""" A property method that returns the thermogram's temperature in
	degrees celsius (°C).
	
	Returns
	-------
	Array[np.float64, ..., ...]
		A 2D array of numpy float values in celsius. Order is [H, W].
	"""
	vals = kelvin(vals)
	#print(" postkelvin = " + str(vals[0]))

	for i in range(len(vals)):
		vals[i]=vals[i] - 273.15
	#print(" postcelcius = " + str(vals[0]))
	return vals

def fahrenheit(vals):
	""" A property method that returns the thermogram's temperature in
	degrees fahrenheit (°F).
	
	Returns
	-------
	Array[np.float64, ..., ...]
		A 2D array of numpy float values in fahrenheit. Order is [H, W].
	"""

	vals = celsius(vals)
	#print(" postcelsius = " + str(vals[0]))

	for i in range(len(vals)):
		vals[i]=vals[i] * 1.8 + 32.00
	#print(" postfahrenheit = " + str(vals[0]))
	return vals

class Colormaps(IntEnum):
	COLORMAP_AUTUMN = 0
	COLORMAP_BONE = 1
	COLORMAP_CIVIDIS = 17
	COLORMAP_COOL = 8
	COLORMAP_HOT = 11
	COLORMAP_HSV = 9
	COLORMAP_INFERNO = 14
	COLORMAP_JET = 2
	COLORMAP_MAGMA = 13
	COLORMAP_OCEAN = 5
	COLORMAP_PARULA = 12
	COLORMAP_PINK = 10
	COLORMAP_PLASMA = 15
	COLORMAP_RAINBOW = 4
	COLORMAP_SPRING = 7
	COLORMAP_SUMMER = 6
	COLORMAP_TURBO = 20
	COLORMAP_TWILIGHT = 18
	COLORMAP_TWILIGHT_SHIFTED = 19
	COLORMAP_VIRIDIS = 16
	COLORMAP_WINTER = 3

colormaps = [
	cv2.COLORMAP_AUTUMN,
	cv2.COLORMAP_BONE,
	cv2.COLORMAP_JET,
	cv2.COLORMAP_WINTER,
	cv2.COLORMAP_RAINBOW,
	cv2.COLORMAP_OCEAN,
	cv2.COLORMAP_SUMMER,
	cv2.COLORMAP_SPRING,
	cv2.COLORMAP_COOL,
	cv2.COLORMAP_HSV,
	cv2.COLORMAP_PINK,
	cv2.COLORMAP_HOT,
	cv2.COLORMAP_PARULA,
	cv2.COLORMAP_MAGMA,
	cv2.COLORMAP_INFERNO,
	cv2.COLORMAP_PLASMA,
	cv2.COLORMAP_VIRIDIS,
	cv2.COLORMAP_CIVIDIS,
	cv2.COLORMAP_TWILIGHT,
	cv2.COLORMAP_TWILIGHT_SHIFTED,
	cv2.COLORMAP_TURBO,
]

filelist = sorted([x for x in os.listdir(".") if x.lower().endswith('.csq') and not os.path.isdir(x)])
for file in filelist:
	name = file[0:file.rfind('.')]
	
	if not os.path.isdir(name):
		os.mkdir(name)
	if not os.path.isdir(name + "\\fff"):
		os.mkdir(name + "\\fff")
	if not os.path.isdir(name + "\\jpgls"):
		os.mkdir(name + "\\jpgls")
	if not os.path.isdir(name + "\\png16"):
		os.mkdir(name + "\\png16")
	if not os.path.isdir(name + "\\png16-calibrated"):
		os.mkdir(name + "\\png16-calibrated")
	if not os.path.isdir(name + "\\png8"):
		os.mkdir(name + "\\png8")
	
	print(" " + file + "... .  .   .")
	print("  fff... .  .   .")
	if os.path.isfile(name + "\\fff\\" + name + "_000001.fff"):
		print("   exists..")
	else:
		csplitb = CSplitB("46464600525450", file, 6, name + "\\fff\\" + name + "_", '.fff')
		csplitb.run()
	
	print("  jpegls... .  .   .")
	if os.path.isfile(name + "\\jpgls\\" + name + "_000001.jpgls"):
		print("   exists..")
		with open(name + "\\exif.json", 'r') as handle:
			exifdata = json.load(handle)
	else:
		with exiftool.ExifTool() as et:
			# et.run()
			ett = et.execute(
				name + "\\fff\\" + name + "_000001.fff"
			)
			#print(et.last_stdout)
			exifstring=et.last_stdout # straight text
			exiflines=exifstring.strip().split('\n') # in lines
			exifdata=dict()
			for exifline in exiflines:
				exifheader=exifline[:exifline.index(':')].strip() # dirty header
				exifvalue=exifline[exifline.index(':')+1:].strip() # dirty value

				if ']' in exifheader:
					exifheader=exifheader[exifheader.index(']')+1:].strip() # clean header
				exifheader=exifheader.replace(' ','')

				try:
					exifvalue=float(exifvalue) # parse number values
				except Exception:
					pass # it's ok, turns out it was not float

				# if '.' in exifvalue: # parse number values
				# 	try:
				# 		exifvalue=float(exifvalue)
				# 	except Exception:
				# 		pass # it's ok, turns out it was not float
				# else:
				# 	try:
				# 		exifvalue=int(exifvalue)
				# 	except Exception:
				# 		pass # it's ok, turns out it was not int

				exifdata[exifheader]=exifvalue

			with open(name + "\\exif.json", 'w') as handle: # saving just for fun
				json.dump(exifdata, handle, indent=4, sort_keys=True)

			ett = et.execute(
				"-b",
				"-RawThermalImage",
				name + "\\fff\\" + name + "_*.fff",
				"-w",
				name + "\\jpgls\\%f.jpgls"
			)
			print(et.last_stderr)
	
	print("  png16... .  .   .")
	if os.path.isfile(name + "\\png16\\" + name + "_000001.png"):
		print("   exists..")
	else:
		(
			ffmpeg.input(name + "\\jpgls\\" + name + "_%06d.jpgls", f='image2')
			.output(name + "\\png16\\" + name + "_%06d.png", pix_fmt='gray16be')
			.run()
		)
	# "ffmpeg -f image2 -vcodec jpegls -i 'frame%05d.tiff' -pix_fmt gray16be -vcodec png 'file.avi'"
	# ">ffmpeg -f image2 -vcodec jpegls -start_number 101 -i _seq%3d.jpgls output.mp4"
	
	pnglist = sorted([x for x in os.listdir(name + "\\png16") if x.lower().endswith('.png') and not os.path.isdir(x)])
	
	imgmin = None
	imgmax = None
	idx = 0
	pct = -1
	listlen = len(pnglist)
	if os.path.isfile(name + "\\minmax.pickle"):
		with open(name + "\\minmax.pickle", 'rb') as handle:
			[imgmin, imgmax] = pickle.load(handle)
	else:
		print("   finding min/max...")
		for pngidx in range(listlen):
			pngfile = pnglist[pngidx]
			idx += 1
			newpct = round(idx * 100 / listlen)
			if newpct != pct:
				pct = newpct
				sys.stdout.write("\r[" + ("#" * pct) + (" " * (100 - pct)) + "] " + str(pct) + "%")
			# print(str(pct)+"%")
			img = cv2.imread(name + "\\png16\\" + pngfile, cv2.IMREAD_UNCHANGED).astype(np.float32)
			if imgmin is None:
				imgmin = np.min(img)
				imgmax = np.max(img)
			else:
				imgmin = np.min([imgmin, np.min(img)])
				imgmax = np.max([imgmax, np.max(img)])
		print()

		with open(name + "\\minmax.pickle", 'wb') as handle:
			pickle.dump([imgmin, imgmax], handle)
	with open(name + "\\minmax.json", 'w') as handle:
		json.dump([float(imgmin), float(imgmax)], handle)

	print("min "+ str(imgmin)+" - max "+str(imgmax))

	# print("  png8... .  .   .")
	# if os.path.isfile(name + "\\png8\\" + name + "_000001.png"):
	# 	print("   exists..")
	# else:
	# 	idx = 0
	# 	pct = -1
	# 	for pngidx in range(listlen):
	# 		pngfile = pnglist[pngidx]
	# 		idx += 1
	# 		newpct = round(idx * 100 / listlen)
	# 		if newpct != pct:
	# 			pct = newpct
	# 			sys.stdout.write("\r[" + ("#" * pct) + (" " * (100 - pct)) + "] " + str(pct) + "%")
	# 		# print(str(pct)+"%")
	# 		img = cv2.imread(name + "\\png16\\" + pngfile, cv2.IMREAD_UNCHANGED).astype(np.float32)
	# 		# Rescale to 8 bit
	# 		img = 255 * (img - imgmin) / (imgmax - imgmin)
	# 		# Apply colourmap - try COLORMAP_JET if INFERNO doesn't work.
	# 		# https://docs.opencv.org/3.4/d3/d50/group__imgproc__colormap.html#ga9a805d8262bcbe273f16be9ea2055a65
	# 		if idx==1:
	# 			for colormap in colormaps:
	# 				img_col = cv2.applyColorMap(img.astype(np.uint8), colormap)
	# 				cv2.imwrite(str(Colormaps(colormap).name) +".png", img_col)
	# 		img_col = cv2.applyColorMap(img.astype(np.uint8), cv2.COLORMAP_MAGMA)
	# 		cv2.imwrite(name + "\\png8\\" + pngfile, img_col)
	# 	print()

	print("  png16-calibrated... .  .   .")
	if os.path.isfile(name + "\\png16-calibrated\\" + name + "_000001.png"):
		print("   exists..")
	else:
		idx = 0
		pct = -1
		for pngidx in range(listlen):
			pngfile = pnglist[pngidx]
			idx += 1
			newpct = round(idx * 100 / listlen)
			if newpct != pct:
				pct = newpct
				sys.stdout.write("\r[" + ("#" * pct) + (" " * (100 - pct)) + "] " + str(pct) + "%")
			# print(str(pct)+"%")
			img = cv2.imread(name + "\\png16\\" + pngfile, cv2.IMREAD_UNCHANGED).astype(np.float32)
			print()
			print(" src = "+str(img[0][0]))
			celsius(img.flat)
			print(" out = "+str(img[0][0]))

			print(" mintemp: "+ str( np.min(img)))
			print(" maxtemp: "+ str( np.max(img)))
			print()
			print(img.shape)
			exit()
			# Rescale to 8 bit
			img = 65535.0 * (img - imgmin) / (imgmax - imgmin)
			# Apply colourmap - try COLORMAP_JET if INFERNO doesn't work.
			# https://docs.opencv.org/3.4/d3/d50/group__imgproc__colormap.html#ga9a805d8262bcbe273f16be9ea2055a65
			if idx==1:
				for colormap in colormaps:
					img_col = cv2.applyColorMap(img.astype(np.uint8), colormap)
					cv2.imwrite(str(Colormaps(colormap).name) +".png", img_col)
			img_col = cv2.applyColorMap(img.astype(np.uint8), cv2.COLORMAP_MAGMA)
			cv2.imwrite(name + "\\png16-calibrated\\" + pngfile, img_col)
		print()

	print("  mp4... .  .   .")
	if os.path.isfile(name + ".mp4"):
		print("   exists..")
	else:
		(
			ffmpeg.input(name + "\\png8\\" + name + "_%06d.png", f='image2')
			.output(
				name + ".mp4",
				vcodec="libx265",
				crf=10,
			)
			.run()
		)
