import sys
import os
import shutil
from csplitb import CSplitB
from ffmpeg import FFmpeg, Progress
import exiftool
import cv2
import numpy as np
import pickle
import json
from enum import IntEnum

##### options

create_png_16bit_linear=True
create_png_16bit_celcius=False
create_png_8bit=False
create_mp4=True
create_gradientbox=True
create_colormap_examples=True

targetcolormap = cv2.COLORMAP_TURBO

delete_intermediates=True
delete_png_16bit_raw=True
delete_png_8bit=True

#####

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


# note, exif only extracted from first frame with assumption values do not change during recording.. modify code if they do
exifdata = None # exif will be here later
PlanckR1 = None
PlanckR2 = None
PlanckB = None
PlanckO = None
PlanckF = None

def raw_to_kelvin(val):
	return PlanckB / np.log( (PlanckR1 / PlanckR2) * (1. / (val + PlanckO) ) + PlanckF)

def raw_to_celcius(val):
	return raw_to_kelvin(val) - 273.15

def raw_to_fahrenheit(val):
	return raw_to_celcius(val) * 1.8 + 32.00

def gradientbox(width,height,minval,maxval):
	img=np.zeros((height,width, 1), np.uint16)
	for y in range(height):
		cv2.line(img, (0, y) ,(width, y), float(height-y)/float(height)*(maxval-minval)+minval )
	return img


filelist = sorted([x for x in os.listdir(".") if x.lower().endswith('.csq') and not os.path.isdir(x)])
for file in filelist:
	name = file[0:file.rfind('.')]
	
	if not os.path.isdir(name):
		os.mkdir(name)

	_create_png_8bit = create_png_8bit or ( create_mp4 and not os.path.isfile(name + ".mp4") and ( not os.path.isfile(name + "\\png8\\" + name + "_000001.png") ) )  # required by mp4
	_create_png_16bit_linear = create_png_16bit_linear or ( _create_png_8bit and ( not os.path.isfile(name + "\\png8\\" + name + "_000001.png") ) )  # required by 8bit
	# print("_create_png_8bit " + str(_create_png_8bit))
	# print("_create_png_16bit_linear " + str(_create_png_16bit_linear))

	print(" " + file + "... .  .   .")
	print("  fff... .  .   .")
	if not os.path.isdir(name + "\\fff"):
		os.mkdir(name + "\\fff")
	if os.path.isfile(name + "\\fff\\" + name + "_000000.fff") or os.path.isfile(name + "\\png16-raw\\" + name + "_000001.png") or os.path.isfile(name + "\\png16-linear\\" + name + "_000001.png"): # fff are 0-indexed
		print("   exists..")
	else:
		csplitb = CSplitB("46464600525450", file, 6, name + "\\fff\\" + name + "_", '.fff')
		csplitb.run()

	print("  exif... .  .   .")
	if os.path.isfile(name + "\\exif.json"):
		print("   exists..")
		with open(name + "\\exif.json", 'r') as handle:
			exifdata = json.load(handle)
	else:
		with exiftool.ExifTool() as et:
			# et.run()
			ett = et.execute(
				name + "\\fff\\" + name + "_000000.fff"  # fff are 0-indexed
			)
			# print(et.last_stdout)
			exifstring = et.last_stdout  # straight text
			exiflines = exifstring.strip().split('\n')  # in lines
			exifdata = dict()
			for exifline in exiflines:
				exifheader = exifline[:exifline.index(':')].strip()  # dirty header
				exifvalue = exifline[exifline.index(':') + 1:].strip()  # dirty value

				if ']' in exifheader:
					exifheader = exifheader[exifheader.index(']') + 1:].strip()  # clean header
				exifheader = exifheader.replace(' ', '')

				try:
					exifvalue = float(exifvalue)  # parse number values
				except Exception:
					pass  # it's ok, turns out it was not float

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

				exifdata[exifheader] = exifvalue

			with open(name + "\\exif.json", 'w') as handle:
				json.dump(exifdata, handle, indent=4, sort_keys=True)

	PlanckR1 = exifdata['PlanckR1']
	PlanckR2 = exifdata['PlanckR2']
	PlanckB = exifdata['PlanckB']
	PlanckO = exifdata['PlanckO']
	PlanckF = exifdata['PlanckF']

	listlen = len([x for x in os.listdir(name + "\\fff") if x.lower().endswith('.fff') and not os.path.isdir(x)])

	print("  jpegls... .  .   .")
	if not os.path.isdir(name + "\\jpgls"):
		os.mkdir(name + "\\jpgls")
	if os.path.isfile(name + "\\jpgls\\" + name + "_000000.jpgls") or os.path.isfile(name + "\\png16-raw\\" + name + "_000001.png") or os.path.isfile(name + "\\png16-linear\\" + name + "_000001.png"): # jpgls are 0-indexed
		print("   exists..")
	else:
		with exiftool.ExifTool() as et:
			ett = et.execute(
				"-b",
				"-RawThermalImage",
				name + "\\fff\\" + name + "_*.fff",
				"-w",
				name + "\\jpgls\\%f.jpgls"
			)
			if len(et.last_stderr.strip())>0:
				print(et.last_stderr)

	if delete_intermediates:
		shutil.rmtree(name + "\\fff")

	print("  png16-raw... .  .   .")
	if not os.path.isdir(name + "\\png16-raw"):
		os.mkdir(name + "\\png16-raw")
	if os.path.isfile(name + "\\png16-raw\\" + name + "_000001.png") or os.path.isfile(name + "\\png16-linear\\" + name + "_000001.png"):
		print("   exists..")
	else:
		ffmpeg = (
			FFmpeg()
			.input(
				name + "\\jpgls\\" + name + "_%06d.jpgls",
				f='image2',
				# loglevel="quiet",
				# stats=None,
				# hide_banner=None,
			)
			.output(name + "\\png16-raw\\" + name + "_%06d.png", pix_fmt='gray16be')
		)
		@ffmpeg.on("progress")
		def ffmpeg_progress(progress: Progress):
			pct = round(progress.frame * 100 / listlen)
			sys.stdout.write("\r   [" + ("#" * pct) + (" " * (100 - pct)) + "] " + str(pct) + "%")
			# print(progress)
		ffmpeg.execute()
		print()

	if delete_intermediates:
		shutil.rmtree(name + "\\jpgls")

	
	imgmin = None
	imgmax = None
	imgCmin = None
	imgCmax = None
	idx = 0
	pct = -1
	print("  finding min/max... .  .   .")
	if os.path.isfile(name + "\\minmax.json"):
		print("   exists..")
		with open(name + "\\minmax.json", 'r') as handle:
			minmaxobj=json.load(handle)
			imgmin = minmaxobj['min']
			imgmax = minmaxobj['max']
			imgCmin = raw_to_celcius(imgmin)
			imgCmax = raw_to_celcius(imgmax)
	else:
		pnglist = sorted([x for x in os.listdir(name + "\\png16-raw") if x.lower().endswith('.png') and not os.path.isdir(x)])
		listlen = len(pnglist)
		for pngidx in range(listlen):
			pngfile = pnglist[pngidx]
			idx += 1
			newpct = round(idx * 100 / listlen)
			if newpct != pct:
				pct = newpct
				sys.stdout.write("\r   [" + ("#" * pct) + (" " * (100 - pct)) + "] " + str(pct) + "%")
			# print(str(pct)+"%")
			img = cv2.imread(name + "\\png16-raw\\" + pngfile, cv2.IMREAD_UNCHANGED).astype(np.float32)
			if imgmin is None:
				imgmin = np.min(img)
				imgmax = np.max(img)
			else:
				imgmin = np.min([imgmin, np.min(img)])
				imgmax = np.max([imgmax, np.max(img)])

		imgCmin = raw_to_celcius(imgmin)
		imgCmax = raw_to_celcius(imgmax)
		print()

		with open(name + "\\minmax.json", 'w') as handle:
			minmaxobj=dict()
			minmaxobj['min']=float(imgmin)
			minmaxobj['max']=float(imgmax)
			minmaxobj['minCelsius']=imgCmin
			minmaxobj['maxCelsius']=imgCmax
			json.dump(minmaxobj, handle, indent=4, sort_keys=False)

	print("    min "+ str(imgmin)+" - max "+str(imgmax))
	print("    Celcius min "+ str(imgCmin)+" - max "+str(imgCmax))

	if _create_png_16bit_linear:
		print("  png16-linear... .  .   .")
		if not os.path.isdir(name + "\\png16-linear"):
			os.mkdir(name + "\\png16-linear")
		if os.path.isfile(name + "\\png16-linear\\" + name + "_000001.png"):
			print("   exists..")
		else:
			idx = 0
			pct = -1
			pnglist = sorted([x for x in os.listdir(name + "\\png16-raw") if x.lower().endswith('.png') and not os.path.isdir(x)])
			listlen = len(pnglist)
			for pngidx in range(listlen):
				pngfile = pnglist[pngidx]
				idx += 1
				newpct = round(idx * 100 / listlen)
				if newpct != pct:
					pct = newpct
					sys.stdout.write("\r   [" + ("#" * pct) + (" " * (100 - pct)) + "] " + str(pct) + "%")
				# print(str(pct)+"%")
				img = cv2.imread(name + "\\png16-raw\\" + pngfile, cv2.IMREAD_UNCHANGED).astype(np.float32)
				#print()
				#print(" src = "+str(img[0][0]))

				# to float kelvin values
				img=raw_to_kelvin(img)

				# to float celsius values
				# img=raw_to_celcius(img)
				#print(" celcius = "+str(img[0][0]))

				# to float fahrenheit values
				# img=raw_to_fahrenheit(img)

				#print(" mintemp: "+ str( np.min(img)))
				#print(" maxtemp: "+ str( np.max(img)))
				#print(" minCtemp: "+ str( imgCmin))
				#print(" maxCtemp: "+ str( imgCmax))

				imgKmin = raw_to_kelvin(imgmin)
				imgKmax = raw_to_kelvin(imgmax)

				# Rescale to 16 bit full range
				img = 65535.0 * (img - imgKmin) / (imgKmax - imgKmin)
				cv2.imwrite(name + "\\png16-linear\\" + pngfile, img.astype(np.uint16))
				#exit()
			print()

	if create_png_16bit_celcius:
		print("  png16-celcius... .  .   .")
		if not os.path.isdir(name + "\\png16-celcius"):
			os.mkdir(name + "\\png16-celcius")
		if os.path.isfile(name + "\\png16-celcius\\" + name + "_000001.png"):
			print("   exists..")
		else:
			idx = 0
			pct = -1
			pnglist = sorted([x for x in os.listdir(name + "\\png16-raw") if x.lower().endswith('.png') and not os.path.isdir(x)])
			listlen = len(pnglist)
			for pngidx in range(listlen):
				pngfile = pnglist[pngidx]
				idx += 1
				newpct = round(idx * 100 / listlen)
				if newpct != pct:
					pct = newpct
					sys.stdout.write("\r   [" + ("#" * pct) + (" " * (100 - pct)) + "] " + str(pct) + "%")
				# print(str(pct)+"%")
				img = cv2.imread(name + "\\png16-raw\\" + pngfile, cv2.IMREAD_UNCHANGED).astype(np.float32)
				#print()
				#print(" src = "+str(img[0][0]))

				# to float kelvin values
				# img=raw_to_kelvin(img)

				# to float celsius values
				img=raw_to_celcius(img) # celcius
				#print(" celcius = "+str(img[0][0]))

				# to float fahrenheit values
				# img=raw_to_fahrenheit(img)

				#print(" mintemp: "+ str( np.min(img)))
				#print(" maxtemp: "+ str( np.max(img)))
				#print(" minCtemp: "+ str( imgCmin))
				#print(" maxCtemp: "+ str( imgCmax))

				# imgKmin = raw_to_kelvin(imgmin)
				# imgKmax = raw_to_kelvin(imgmax)

				# Rescale to 16 bit full range
				# img = 65535.0 * (img - imgKmin) / (imgKmax - imgKmin)

				img = img * 100.0
				# can't save floats in images, so 100x means 12.34c -> 1234 (uint)
				# this allows temperature range of 0c-655.35c in 16bit format

				cv2.imwrite(name + "\\png16-celcius\\" + pngfile, img.astype(np.uint16))
				#exit()
			print()


	if delete_png_16bit_raw:
		shutil.rmtree(name + "\\png16-raw")

	if _create_png_8bit:
		print("  png8... .  .   .")
		if not os.path.isdir(name + "\\png8"):
			os.mkdir(name + "\\png8")
		if os.path.isfile(name + "\\png8\\" + name + "_000001.png"):
			print("   exists..")
		else:
			pnglist = sorted([x for x in os.listdir(name + "\\png16-linear") if x.lower().endswith('.png') and not os.path.isdir(x)])
			listlen = len(pnglist)
			idx = 0
			pct = -1
			for pngidx in range(listlen):
				pngfile = pnglist[pngidx]
				idx += 1
				newpct = round(idx * 100 / listlen)
				if newpct != pct:
					pct = newpct
					sys.stdout.write("\r   [" + ("#" * pct) + (" " * (100 - pct)) + "] " + str(pct) + "%")
				# print(str(pct)+"%")
				img = cv2.imread(name + "\\png16-linear\\" + pngfile, cv2.IMREAD_UNCHANGED).astype(np.float32)
				# Rescale to 8 bit
				# img = 255.0 * (img - float(imgCmin)) / (float(imgCmax) - float(imgCmin))
				img = img * (255.0/65535.0)
				# Apply colourmap - try COLORMAP_JET if INFERNO doesn't work.
				# https://docs.opencv.org/3.4/d3/d50/group__imgproc__colormap.html#ga9a805d8262bcbe273f16be9ea2055a65
				if idx==1 and create_colormap_examples:
					for colormap in colormaps:
						img_col = cv2.applyColorMap(img.astype(np.uint8), colormap)
						cv2.imwrite(name + "\\" + str(Colormaps(colormap).name) + ".png", img_col)
				img_col = cv2.applyColorMap(img.astype(np.uint8), targetcolormap)
				# img_col = img
				cv2.imwrite(name + "\\png8\\" + pngfile, img_col)
			print()

	if create_mp4:
		fps=exifdata['FrameRate']
		print("  mp4... .  .   .")
		if os.path.isfile(name + ".mp4"):
			print("   exists..")
		else:
			ffmpeg = (
				FFmpeg()
				.input(
					name + "\\png8\\" + name + "_%06d.png",
					f='image2',
					framerate=fps,
				)
				.output(
					name + ".mp4",
					vcodec="libx265",
					vf="scale=iw*2:ih*2", # 2x upscale because of chroma subsampling
					crf=10,
				)
			)
			@ffmpeg.on("progress")
			def ffmpeg_progress(progress: Progress):
				pct = round(progress.frame * 100 / listlen)
				sys.stdout.write("\r   [" + ("#" * pct) + (" " * (100 - pct)) + "] " + str(pct) + "%")
				# print(progress)
			ffmpeg.execute()
			print()

	if delete_png_8bit and os.path.isdir(name + "\\png8"):
		shutil.rmtree(name + "\\png8")

	if create_gradientbox:
		gradientImg = gradientbox(500, 1000, 0, 65535.0)
		cv2.imwrite(name + "\\gradient_16bit.png", (gradientImg).astype(np.uint16))
		gradientImg = gradientImg / 65535.0 * 255.0
		gradientImg = cv2.applyColorMap(gradientImg.astype(np.uint8), targetcolormap)
		cv2.imwrite(name + "\\gradient_8bit_colormap.png", gradientImg.astype(np.uint8))

