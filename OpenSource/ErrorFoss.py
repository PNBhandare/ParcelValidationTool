import math
from Parcel import Parcel
import re
import urllib.parse, urllib.request, os, json
import sys
import osgeo
from osgeo import ogr

class Error:

	def __init__(self,featureClass,coName):
		self.coName = coName
		self.generalErrorCount = 0
		self.geometricErrorCount = 0
		self.addressErrorCount = 0
		self.taxErrorCount = 0
		self.comparisonDict = {}
		self.attributeFileErrors = []
		self.geometricFileErrors = []
		self.geometricPlacementErrors = []
		self.pinSkipCount = 0
		self.uniqueParcelDateDict = {}
		self.uniqueparcelDatePercent = 0.0
		self.trYearPast = 0
		self.trYearExpected = 0
		self.trYearFuture = 0
		self.trYearOther = 0
		self.coNameMiss = 0
		self.fipsMiss = 0
		self.srcMiss = 0
		self.netMoreGrsCnt = 0
		self.recordIterationCount = 0
		self.recordTotalCount = featureClass.GetFeatureCount() # Total number of records in the feature class
		self.checkEnvelopeInterval = math.trunc(self.recordTotalCount / 100) #Interval value used to apply 10 total checks on records at evenly spaced intervals throughout the dataset.
		self.nextEnvelopeInterval = self.checkEnvelopeInterval
		self.notConfirmGeomCount = 0 #counts parcels with invalid Geometry
		self.validatedGeomCount = 0 #counts parcels whose geometry is validated
		self.geometryNotValidated = False
		self.geometryNotChecked = True
		self.mflLnd = 0
		self.diffxy = 0
		self.xyShift = 0
		self.codedDomainfields = []
		self.badcharsCount = 0
		self.ErrorSum = 0   #sum of generalErrorCount, geometricErrorCount, addressErrorCount, taxErrorCount
		self.flags_dict = {'numericCheck': 0, 'duplicatedCheck': 0, 'prefixDom': 0, 'streettypeDom': 0, 'unitidtype': 0, 'placenameDom': 0, 'suffixDom': 0, 'trYear': 0, 'taxrollYr': 0, 'streetnameDom': 0, 'zipCheck': 0, 'cntCheck': 0, 'redundantId': 0, 'postalCheck':0, 'auxPropCheck': 0, 'fairmarketCheck': 0, 'mflvalueCheck': 0, 'auxclassFullyX4': 0, 'cntPropClassCheck': 0, 'matchContrib': 0, 'netvsGross': 0, 'schoolDist': 0 }

	# Test records throughout the dataset to ensure that polygons exist within an actual county envelope 
	#("Waukesha" issue or the "Lake Michigan" issue).
	def checkGeometricQuality(self,Parcel,ignoreList):
		if self.nextEnvelopeInterval == self.recordIterationCount:
			if str(Parcel.parcelid).upper() in ignoreList:   
				self.nextEnvelopeInterval = self.nextEnvelopeInterval + 1
			else:
				countyEnvelope = self.testCountyEnvelope(Parcel)
				if countyEnvelope == "Valid" and self.validatedGeomCount == 50: # would mean that the "Waukesha" issue or the "Lake Michigan" issue does not exist in this dataset.
					self.nextEnvelopeInterval = 4000000
					if self.notConfirmGeomCount > 0:
						self.xyShift = round((self.diffxy/self.notConfirmGeomCount),2)
					print("    Parcel geometry validated.")
					self.geometricPlacementErrors = []
				elif countyEnvelope == "Not Confirmed" and self.notConfirmGeomCount == 50:
					self.nextEnvelopeInterval = 4000000
					self.xyShift = round((self.diffxy/self.notConfirmGeomCount),2)
					#print("couldn't validate")
					if  self.xyShift >= 6:
						self.geometryNotValidated = True
						print("\n    Parcel geometry not validated, several parcel geometries appear to be spatially misplaced by about: " + str(self.xyShift) + " meters. \n" )
					
					elif self.xyShift >= 1.2 and self.xyShift < 6:
						print("\n  Parcel geometry validated, but several parcel geometries appear to be spatially misplaced by about: " + str(self.xyShift) + " meters. \n" )
						self.geometricPlacementErrors = ["Several parcel geometries appear to be spatially misplaced " + str(self.xyShift) + " meters when comparing them against parcel geometries from last year. This issue is indicative of a re-projection error. Please see the following documentation: http://www.sco.wisc.edu/parcels/tools/FieldMapping/Parcel_Schema_Field_Mapping_Guide.pdf section #2, for advice on how to project native data to the Statewide Parcel CRS."]
					else:
						print("\n    Parcel geometry validated.")
						self.geometricPlacementErrors = []
				self.nextEnvelopeInterval = self.nextEnvelopeInterval + self.checkEnvelopeInterval
		elif self.nextEnvelopeInterval < 4000000 and self.nextEnvelopeInterval >= (100 * self.checkEnvelopeInterval):  #all possible checks
			if self.validatedGeomCount == 0 and self.notConfirmGeomCount == 0: #no parcel geometry was checked -- likely ParcelIds are different from previous years
				#print("The PARCELID within the dataset may not match the PARCELID submitted the previous year. \n" )
				self.nextEnvelopeInterval = 4000000
				print("    Parcel geometry not validated yet.")
				self.geometryNotChecked = False   # flag for county centroid check funcion
			elif self.notConfirmGeomCount  > 0:
				self.nextEnvelopeInterval = 4000000
				self.xyShift = round((self.diffxy/self.notConfirmGeomCount),2)
				# print("  Several parcel geometries appear to be spatially misplaced by about: " + str(self.xyShift) + " meters." )
				self.geometricPlacementErrors = ["Several parcel geometries appear to be spatially misplaced " + str(self.xyShift) + " meters when comparing them against parcel geometries from last year. This issue is indicative of a re-projection error. Please see the following documentation: http://www.sco.wisc.edu/parcels/tools/FieldMapping/Parcel_Schema_Field_Mapping_Guide.pdf section #2, for advice on how to project native data to the Statewide Parcel CRS."]
		self,Parcel = self.testParcelGeometry(Parcel,ignoreList)
		self.recordIterationCount += 1
		return (self, Parcel)

	# Will test the row against LTSB's feature service to identify if the feature is in the correct location.
	def testCountyEnvelope(self, Parcel):
		specialchars = ['/', '#', '&']  #this special characters occurs in some ParcelIDs
		charsdict = {'&': '%26', '#': '%23', '/': '%2F'}
		parcelid =  str(Parcel.parcelid).upper()
		for i in specialchars:
			while parcelid is not None and i in parcelid:
				parcelid = parcelid[:parcelid.find(i)] + charsdict[i] + parcelid[parcelid.find(i)+1:]
		try:
			#baseURL = "http://mapservices.legis.wisconsin.gov/arcgis/rest/services/WLIP/Parcels/FeatureServer/0/query"
			baseURL = "https://services3.arcgis.com/n6uYoouQZW75n5WI/arcgis/rest/services/Wisconsin_Statewide_Parcels/FeatureServer/0/query"
			where =  str(Parcel.parcelfips) + parcelid
			#query = "?f=json&where=STATEID+%3D+%27{0}%27&geometry=true&returnGeometry=true&spatialRel=esriSpatialRelIntersects&outFields=OBJECTID%2CPARCELID%2CTAXPARCELID%2CCONAME%2CPARCELSRC&outSR=3071&resultOffset=0&resultRecordCount=10000".format(where)
			query = '?where=STATEID+%3D++%27{0}%27&geometry=&spatialRel=esriSpatialRelIntersects&outFields=OBJECTID%2C+PARCELID%2C+CONAME%2C+PARCELSRC&returnGeometry=true&outSR=3071&resultOffset=0&resultRecordCount=10000&f=pjson&token='.format(where)
			fsURL = baseURL + query
			#fs.load(fsURL)
			fp = urllib.request.urlopen(fsURL)			
			mybytes = fp.read()
			currFC = mybytes.decode('utf_8')
			currEsriJSON = json.loads(currFC)
			fp.close()
			
			#centroidXY = LinearRing([tuple(coord) for coord in currGeoJSON['features'][0]['geometry']['rings'][0]]).centroid
			# convert esriJson to geoJson; select the rings, then make a geojson string to create a ogr.geometry 
			rings  =  currEsriJSON['features'][0]['geometry']['rings']   #there may be more than two rings in the case of multipolys
			str_geoJSON = """{"type":"Polygon","coordinates":""" + str(rings) + "}"
			centroidXY = ogr.CreateGeometryFromJson(str_geoJSON).Centroid()
			v1x, v1y = tuple ([centroidXY.GetX(), centroidXY.GetY()])
			#v2x, v2y = LinearRing(tuple(coord) for coord in Parcel.geometry).centroid   
			geom =  Parcel.shapeXY    ## inFC centroid
			v2x, v2y = tuple ([geom.GetX(), geom.GetY()])
			v1x = round(v1x,2)
			v2x = round(v2x,2)
			v1y = round(v1y,2)
			v2y = round(v2y,2)
			diffx = v2x - v1x
			diffy = v2y - v1y
			if diffx == 0 and diffy == 0: #(v2x == v1x) and (v2y == v1y):
				self.validatedGeomCount += 1
				diffxy = round(math.sqrt (diffx*diffx + diffy*diffy),2)  #distance btw the two centroid points
				#print ("\nParcel id  " + str (Parcel.parcelid))
				#print ( "Validated --- distance  " + str(diffxy))
				if (self.validatedGeomCount % 10 == 0):
					print("    Checking parcel geometry ...\n")
				return "Valid"
			else:
				diffxy = round(math.sqrt (diffx*diffx + diffy*diffy),2)  #distance btw the two centroid points
				#print ("\nParcel id  " + str (Parcel.parcelid))
				#print ( "no confirmed --- distance  " + str(diffxy))
				self.diffxy = self.diffxy + diffxy
				self.notConfirmGeomCount += 1
				#print (parcelid)
				#print ("New coord  " + str (v2x) + ", " + str(v2y) + " and O coord " + str (v1x) + ", " + str(v1y) )
				#print ( diffxy )
				if (self.notConfirmGeomCount % 10 == 0):
					print("    Parcel geometry not validated yet, will attempt another record.")
					#print ("P coord  " + str (v2x) + ", " + str(v2y) + " and O coord " + str (v1x) + ", " + str(v1y) )					
					#print ( "no confirmed --- distance  " + str(diffxy))
				return "Not Confirmed"
				# Call it valid If the query returns no features (failure to return features would not be caused by a misalignment)
			#  return "Valid"
		except:
			# Call it valid if an error happens (error would not be caused by a misalignment)
			return "Valid"
		# return "Valid"

	def testParcelGeometry(self,Parcel,ignoreList):
		# Test for null geometries or other oddities
		parcelid = str(Parcel.parcelid).upper()  ## parcelid not in ignoreList  ## allow oddities in pinskips 
		try:
			geom = Parcel.shapeXY
			xCent = geom.GetX()
			yCent = geom.GetY()
		except:
			Parcel.geometricErrors.append("Corrupt Geometry: The geometry of the feature class could not be accessed.")
			self.geometricErrorCount += 1
		try:
			areaP = Parcel.shapeArea
			lengthP = Parcel.shapeLength
			if areaP < 0.01 and areaP > 0 and (parcelid is None or parcelid not in ignoreList):  ### gdal may create open polygones 
				Parcel.geometricErrors.append("Sliver Polygon: AREA")
				self.geometricErrorCount += 1
			if lengthP < 0.01 and (parcelid is None or parcelid not in ignoreList):
				Parcel.geometricErrors.append("Sliver Polygon: LENGTH")
				self.geometricErrorCount += 1
			if areaP > 0 and (areaP/lengthP) < 0.01 and (parcelid is None or parcelid not in ignoreList):
				#getattr(Parcel, "geometricErrors").append("Sliver Polygon: AREA/LENGTH")
				#setattr(Error, "geometricErrorCount", getattr(Error, "geometricErrorCount") + 1)
				Parcel.geometricErrors.append("Sliver Polygon: AREA/LENGTH")
				self.geometricErrorCount += 1
		except:
			Parcel.geometricErrors.append("Corrupt Geometry: The area and/or length of the feature class could not be accessed.")
			self.geometricErrorCount += 1
		return self,Parcel

	#Check if the coordinate reference system is consistent with that of the parcel initiative (Error object, feature class)
	def checkCRS(self,featureClass):
		try:
			var = True
			shape = True
			coord = True
			## Get coordinate reference system
			#print( "in checkcrs: ")			
			crs = featureClass.GetSpatialRef().ExportToWkt().split(",")[0].split("[")[1].replace('"','')
			# spatialReference = desc.spatialReference
			# Test for the Polygon feature class against the parcel project's, shape type, projection name, and units.
			# if desc.shapeType != "Polygon":

			geomtype = ogr.GeometryTypeToName(featureClass.GetLayerDefn().GetGeomType())
			if 	(geomtype != 'Multi Polygon') & (geomtype != 'Polygon'):
			# Error.geometricFileErrors.append("The feature class should be of polygon type instead of: " + desc.shapeType)
				var = False
				shape = False
			if crs != 'NAD83(HARN) / Wisconsin Transverse Mercator' :   ## "NAD_1983_HARN_Wisconsin_TM":
				#Error.geometricFileErrors.append("The feature class should be 'NAD_1983_HARN_Wisconsin_TM' instead of: " + spatialReference.name + " Please follow this documentation: http://www.sco.wisc.edu/images/stories/publications/V2/tools/FieldMapping/Parcel_Schema_Field_Mapping_Guide.pdf to project native data to the Statewide Parcel CRS")
				var = False
				coord = False
			#return Error
			if var == False:
				print("\n  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
				print("     IMMEDIATE ERROR REQUIRING ATTENTION")
				print("\n  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
				if shape == False:
					print("  THE FEATURE CLASS SHOULD BE OF POLYGON TYPE INSTEAD OF: " + geomtype.upper() + "\n")
					print("  PLEASE MAKE NEEDED ALTERATIONS TO THE FEATURE CLASS AND RUN THE TOOL AGAIN.\n")
					print("  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\n")
					sys.tracebacklimit = 0
					raise NameError("\n     POLYGON GEOMETRY SYSTEM ERROR")
					#exit()
				if coord == False:
					print("  THE FEATURE CLASS SHOULD BE 'NAD_1983_HARN_Wisconsin_TM' INSTEAD OF: " + crs + "\n")
					print("  PLEASE FOLLOW THIS DOCUMENTATION: http://www.sco.wisc.edu/parcels/tools/FieldMapping/Parcel_Schema_Field_Mapping_Guide.pdf TO PROJECT NATIVE DATA TO THE STATEWIDE PARCEL CRS\n")
					print("  PLEASE MAKE NEEDED ALTERATIONS TO THE FEATURE CLASS AND RUN THE TOOL AGAIN.\n")
					print("  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\n")
					sys.tracebacklimit = 0
					raise NameError("\n     COORDINATE REFERENCE SYSTEM ERROR")
					#exit()
		except: # using generic error handling because we don't know what errors to expect yet.
			# print("  The coordinate reference system of the feature class could not be validated. Please ensure that the feature class is projected to the Statewide Parcel CRS. This documentation may be of use in projecting the dataset: http://www.sco.wisc.edu/parcels/tools/FieldMapping/Parcel_Schema_Field_Mapping_Guide.pdf.")
			sys.tracebacklimit = 0
			raise NameError("\n     GEOMETRY/COORDINATE REFERENCE SYSTEM ERROR")
			#exit()

	#Check if text value is a valid number(Error object, Parcel object, field to test, type of error to classify this as, are <Null>s are considered errors?)
	def checkNumericTextValue(Error,Parcel,field,errorType,acceptNull):
		nullList = ["<Null>", "<NULL>", "NULL", " ", ""]
		try:
			stringToTest = getattr(Parcel,field)
			if stringToTest is not None:
				try:
					int(stringToTest)  # or float(stringToTest):
				except ValueError:
					try:
						float(stringToTest)
					except ValueError:
						try:
							if stringToTest in nullList or stringToTest.isspace():
								getattr(Parcel,errorType + "Errors").append("String values of #<Null>#; #NULL# or blanks occurred in " + field.upper() + ". Please correct.")
								setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
								Error.badcharsCount  += 1
								return (Error, Parcel)  #for wrong <null> values
							else:
								getattr(Parcel,errorType + "Errors").append("Value in " + field.upper() + " does not appear to be a numeric value.")
								setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
								Error.flags_dict['numericCheck'] += 1
								return (Error, Parcel)
						except: pass
			else:
				if acceptNull:
					pass
				else:
					getattr(Parcel,errorType + "Errors").append("<Null> Found on " + field.upper())
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					if field == 'parcelfips' :
						Error.flags_dict['matchContrib'] += 1

				return (Error, Parcel)
		except: # using generic error handling because we don't know what errors to expect yet.
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the " + field.upper() + "field. Please inspect the value of this field.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	#Check if duplicates exist within an entire field(Error object, Parcel object, field to test, type of error to classify this as, are <Null>s are considered errors?, list of strings that are expected to be duplicates (to ignore), running list of strings to test against)
	def checkIsDuplicate(Error,Parcel,field,errorType,acceptNull,ignoreList,testList, acceptYears):
		nullList = ["<Null>", "<NULL>", "NULL", ""]
		try:
			stringToTest = getattr(Parcel,field)
			if stringToTest is not None:
				if stringToTest in ignoreList:
					pass
				else:
					if stringToTest in testList:
						getattr(Parcel,errorType + "Errors").append("Appears to be a duplicate value in " + field.upper())
						setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
						Error.flags_dict['duplicatedCheck'] += 1
					else:
						testList.append(stringToTest)
				return (Error, Parcel)
			else:
				if acceptNull:
					pass
				elif field == 'parcelid':
					taxrollyr = getattr (Parcel, "taxrollyear")
					if taxrollyr == acceptYears[0] or taxrollyr == acceptYears[1] or taxrollyr is None:
						getattr(Parcel,errorType + "Errors").append("<Null> value found in " + field.upper() + " field and a value is expected for non-parcel features and non-new taxable parcels..")
						setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)

				else:
					getattr(Parcel,errorType + "Errors").append("<Null> Found on " + field.upper() + " field. ")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
				return (Error, Parcel)
		except: # using generic error handling because we don't know what errors to expect yet.
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the " + field.upper() + " field. Please inspect the value of this field.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	# Error.parcelDateUniquenessCheck(totError, currParcel,"parceldate")  generalErrorCount

	def parcelDateUniquenessCheck(self,Parcel,field,errorType): 
		nullList = ["<Null>", "<NULL>", "NULL",  "   ", " ", ""]
		try:
			parcelDate = getattr(Parcel, field)
			if parcelDate is not None:
				if  parcelDate in nullList or parcelDate.isspace():				
					getattr(Parcel,errorType + "Errors").append("String values of #<Null>#; #NULL# or blanks occurred in " + field.upper() + ". Please correct.")
					setattr(self,errorType + "ErrorCount", getattr(self,errorType + "ErrorCount") + 1)
					self.badcharsCount  +=1   #for wrong <null> values
				else: 
					self.uniqueParcelDateDict.setdefault( parcelDate,0)
					self.uniqueParcelDateDict[ parcelDate ] += 1

		except:
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the PARCELDATE field. Please inspect the value of this field.")
			setattr(self,errorType + "ErrorCount", getattr(self,errorType + "ErrorCount") + 1)
		return (self, Parcel)


	def maxFreq (self ):
		if self.uniqueParcelDateDict:
			inverse = [(value, key) for key, value in self.uniqueParcelDateDict.items()] 
			parcelDateMoreFrequent = max (inverse)
			self.uniqueparcelDatePercent = (parcelDateMoreFrequent[0]/self.recordTotalCount) * 100
		#return self 


	#Check to see if a domain string is within a list (good) otherwise report to user it isn't found..
	def checkDomainString(Error,Parcel,field,errorType,acceptNull,testList):
		nullList = ["<Null>", "<NULL>", "NULL",  "   ", " ", ""]
		try:
			stringToTest = getattr(Parcel,field)
			if field == 'placename':
				if stringToTest is not None:
					if  stringToTest in nullList or stringToTest.isspace() or any(x.islower() for x in stringToTest):
						getattr(Parcel,errorType + "Errors").append("String values of #<Null>#; #NULL# or blanks occurred in " + field.upper() + ". Please correct.")
						setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
						Error.badcharsCount  +=1   #for wrong <null> values
					elif any(substring in stringToTest for substring in testList):
						pass
					else:
						getattr(Parcel,errorType + "Errors").append("Value provided in " + field.upper() + " does not contain required LSAD descriptor.")
						setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
						Error.flags_dict['placenameDom'] += 1
					return (Error,Parcel)

			elif field == 'unitid' or field == 'unittype':
				if (stringToTest is None):
					pass
				elif ( str(stringToTest) in testList) :
					#print("This value is <Null>... or exists in our list..." + str(stringToTest))
					pass
				else:
					getattr(Parcel,errorType + "Errors").append("The value in " + field.upper() + " is not in standardized domain list. Please standarize/spell out values for affected records.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					#Error.flags_dict['unitidtype'] += 1

				return (Error,Parcel)
			else:
				if stringToTest is not None:
					if  stringToTest in nullList or stringToTest.isspace() or any(x.islower() for x in stringToTest):
						getattr(Parcel,errorType + "Errors").append("String values of #<Null>#; #NULL# or blanks occurred in " + field.upper() + ". Please correct.")
						setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
						Error.badcharsCount  +=1   #for wrong <null> values

					elif stringToTest in testList:
						pass
					else:
						getattr(Parcel,errorType + "Errors").append("Value provided in " + field.upper() + " not in acceptable domain list.")
						setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
						Error_string = field + 'Dom'
						Error.flags_dict[Error_string] += 1

					return (Error, Parcel)
				else:
					if acceptNull:
						pass
					else:
						getattr(Parcel,errorType + "Errors").append("<Null> Found on " + field.upper())
						setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					return (Error, Parcel)
		except: # using generic error handling because we don't know what errors to expect yet.
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the " + field.upper() + " field. Please inspect the value of this field.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	#Check to see if taxroll year provided is what expected, old, future or other value (which we plan to ask for explaination in submission form...)
	def trYear(Error,Parcel,field,pinField,errorType,acceptNull,ignoreList,acceptYears):
		nullList = ["<Null>", "<NULL>", "NULL", ""]
		try:
			stringToTest = getattr(Parcel,field)
			pinToTest = getattr(Parcel,pinField)
			if stringToTest is not None:
				if  stringToTest in nullList or stringToTest.isspace():
					getattr(Parcel,errorType + "Errors").append("String values of #<Null>#; #NULL# or blanks occurred in " + field.upper() + ". Please correct.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.badcharsCount  +=1   #for wrong <null> values
				elif stringToTest == acceptYears[0]:
					Error.trYearPast += 1
				elif stringToTest == acceptYears[1]:
					Error.trYearExpected += 1
				elif stringToTest == acceptYears[2] or stringToTest == acceptYears[3]:
					Error.trYearFuture += 1
				else:
					Error.trYearOther += 1
				return (Error, Parcel)
			else:
				if acceptNull:
					pass
				else:
					if pinToTest in ignoreList or pinToTest is None:
						Error.pinSkipCount += 1
					else:
						getattr(Parcel,errorType + "Errors").append("Value in " + field.upper() + " is flagged. See schema definition. In most cases; value should be expected year (" + acceptYears[1] + "); or future year (" + acceptYears[2] + ") if new parcel/split.")
						setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
						Error.flags_dict['trYear'] += 1

			return (Error, Parcel)
		except: # using generic error handling because we don't know what errors to expect yet.
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the " + field.upper() + " field. Please inspect the value of this field.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	#Verify that all tax roll data is <Null> when the record represent a New Parcel (indicated by a future tax roll year)
	def taxrollYrCheck(Error,Parcel,field,errorType,acceptNull,pinField,acceptYears):
		nullList = ["<Null>", "<NULL>", "NULL", ""]
		try:
			taxRollYear = getattr(Parcel,field)
			taxRollFields = {'IMPVALUE': getattr(Parcel, "impvalue"), 'CNTASSDVALUE': getattr(Parcel, "cntassdvalue"),
			'LNDVALUE': getattr(Parcel, "lndvalue"), 'MFLVALUE': getattr(Parcel, "mflvalue"), 'ESTFMKVALUE': getattr(Parcel, "estfmkvalue"),
			'NETPRPTA': getattr(Parcel, "netprpta"), 'GRSPRPTA': getattr(Parcel, "grsprpta"),'ASSDACRES': getattr(Parcel, "assdacres"),
			'PROPCLASS': getattr(Parcel, "propclass"), 'AUXCLASS': getattr(Parcel, "auxclass")}
			probFields = []
			if taxRollYear is not None:
				if taxRollYear == acceptYears[2] or taxRollYear == acceptYears[3]:
					for key, val in taxRollFields.items():    #iteritems():
						if val is not None:
							probFields.append(key)
					if len(probFields) > 0:
						getattr(Parcel,errorType + "Errors").append("Future Year (" + str(taxRollYear) + ") found and " + " / ".join(probFields) + " field(s) is/are not <Null>. A <Null> value is expected in all tax roll data for records annotated with future tax roll years. Please verify.")
						setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
						Error.flags_dict['taxrollYr'] += 1

				else:  #other years are okay
					pass
				return (Error, Parcel)
			elif acceptNull:  # it is null -> TAXROLLYEAR for parcel splits/new parcels may be <Null>
				pass
		except: # using generic error handling because we don't know what errors to expect yet.
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the " + field.upper() + " field. Please inspect the value of this field.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	#Check to see if street name provided is within a list created from V2.
	def streetNameCheck(Error,Parcel,field,siteAddField,errorType,acceptNull,stNameDict,coname):
		nullList = ["<Null>", "<NULL>", "NULL", " ", ""]
		try:
			#county = coname
			stringToTest = getattr(Parcel,field)
			siteAddToTest = getattr(Parcel,siteAddField)
			if stringToTest is not None:
				if  stringToTest in nullList or stringToTest.isspace() or any(x.islower() for x in stringToTest) :
					getattr(Parcel,errorType + "Errors").append("String values of #<Null>#; #NULL# or blanks occurred in " + field.upper() + ". Please correct.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.badcharsCount  +=1   #for wrong <null> values

				elif stringToTest.strip() in stNameDict[coname]:
					pass
				else:
					getattr(Parcel,errorType + "Errors").append("Value provided in " + field.upper() + " does not appear in list created from data of last year. Please verify this value contains only the STREETNAME and street name is correct.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['streetnameDom'] += 1

				return(Error, Parcel)
			else:
				if siteAddToTest is not None and stringToTest is None:
					getattr(Parcel,errorType + "Errors").append(field.upper() + " is <Null> but " + siteAddField.upper() + " is populated. Please ensure elements are in the appropriate field.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['streetnameDom'] += 1

				elif acceptNull:
					pass
				else:
					getattr(Parcel,errorType + "Errors").append("<Null> Found on " + field.upper() + " field and value is expected.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)

				return (Error, Parcel)
		except: # using generic error handling because we don't know what errors to expect yet.
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the " + field.upper() + " field. Please inspect the value of this field.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	#verify that the values provided in the zip field are 5 digits in length and begin with a '5'.
	def zipCheck(Error,Parcel,field,errorType,acceptNull):
		try:
			stringToTest = getattr(Parcel,field)
			if stringToTest is not None:
				if len(stringToTest) == 5 and stringToTest[0] == '5':
					pass
				else:
					getattr(Parcel,errorType + "Errors").append("Value provided in " + field.upper() + " is either not 5 digits long or does not appear to be a Wisconsin zipcode.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['zipCheck'] += 1
				return(Error,Parcel)

			else:
				if acceptNull:
					pass
				else:
					getattr(Parcel,errorType + "Errors").append("<Null> Found on " + field.upper() + " field and value is expected.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['zipCheck'] += 1
				return (Error, Parcel)

		except: # using generic error handling because we don't know what errors to expect yet.
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the " + field.upper() + " field. Please inspect the value of this field.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	#verify that the values provided in the zip4 field is 4 characters long
	def zip4Check(Error,Parcel,field,errorType,acceptNull):
		try:
			stringToTest = getattr(Parcel, field)
			if stringToTest is not None:
				if len(stringToTest) == 4:
					pass
				else:
					getattr(Parcel,errorType + "Errors").append("Value provided in " + field.upper() + " is not 4 digits long.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['zipCheck'] += 1

				return (Error, Parcel)
			elif acceptNull:
				pass
		except:
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the " + field.upper() + " field. Please inspect the value of this field.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return(Error, Parcel)

	#verify that UNITID contains a values if UNITTYPE field contains a value of "UNIT" or "APARTMENT"
	def unittypeAndUnitidCheck(Error,Parcel,field,errorType):
		utypeList = ["APARTMENT", "UNIT",  "CONDOMINIUM" ]
		try:
			stringToTest = getattr(Parcel, field)   #UnitID
			unitTypeToTest = getattr(Parcel, "unittype")
			if stringToTest is not None:
				pass
			elif  unitTypeToTest is not None and unitTypeToTest.upper() in utypeList:
				getattr(Parcel,errorType + "Errors").append("<Null> value found on UNITID field but a value is expected when UNITTYPE field contains a value of #UNIT# or #APARTMENT#. ")
				setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
			return (Error, Parcel)
		except:
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the " + field.upper() + " field. Please inspect the value of this field.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return(Error, Parcel)


	#Verify that value in Improved field is correct based on value provided in Impvalue field...
	#We may want/need to tweak the logic in here depending on how strictly we enforce the value of <Null> allowed in Impvalue field (i.e. Only for non-tax parcels or allow either 0 or <Null>)
	def impCheck(Error,Parcel,field,impValField,errorType):
		try:
			imprTest = getattr(Parcel,field)
			impValue = getattr(Parcel,impValField)
			if imprTest == None and impValue == None:
				pass

			elif (imprTest == None and impValue is not None) or (imprTest is not None and impValue is None):
				getattr(Parcel,errorType + "Errors").append("Value provided in " + field.upper() + " does not correspond with 'IMPVALUE' for this record - please verify.")
				setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
			elif (imprTest.upper() == 'NO' and float(impValue) != 0):
				getattr(Parcel,errorType + "Errors").append("Value provided in " + field.upper() + " does not correspond with 'IMPVALUE' for this record - please verify.")
				setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
			elif (imprTest.upper() == 'YES' and float(impValue) <= 0):
				getattr(Parcel,errorType + "Errors").append("Value provided in " + field.upper() + " does not correspond with 'IMPVALUE' for this record - please verify.")
				setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCounty") + 1)
			return (Error,Parcel)
		except:
			getattr(Parcel,errorType + "Errors").append("An unknown issue occured with the " + field.upper() + " field. Please inspect the value of this field.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error,Parcel)

	#Verify that CNTASSDVALUE is different to LandValue when ImpValue is greater than zero
	def totCheck (Error,Parcel,field,cntassValue,landValue,errorType):
		try:
			impvalue = getattr(Parcel, field)
			cntassvalue = getattr(Parcel, cntassValue)
			lndvalue =  getattr(Parcel, landValue)
			if impvalue is None and cntassvalue is None and lndvalue is None:
				pass
			elif  (impvalue  is None or float(impvalue) == 0):
				if (cntassvalue is not None and lndvalue is not None) and (float(cntassvalue) == float(lndvalue)):
					pass
				elif (cntassvalue is not None and lndvalue is not None) and (float(cntassvalue) != float(lndvalue)):
					getattr(Parcel,errorType + "Errors").append("Value provided in " + field.upper() + " is zero or <Null>. 'CNTASSDVALUE' should be equal to 'LNDVALUE' for this record - please verify.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['cntCheck'] += 1

			elif (impvalue is not None and float(impvalue) > 0):
				if (cntassvalue is not None and lndvalue is not None) and (float(cntassvalue) > float(lndvalue)) :
					pass
				elif (cntassvalue is not None and lndvalue is not None) and (float(cntassvalue) == float(lndvalue)):
					getattr(Parcel,errorType + "Errors").append("Value provided in " + field.upper() + " is greater than zero. 'CNTASSDVALUE' should not be equal to 'LNDVALUE' for this record - please verify.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)  #Error.taxErrorCount +=
					Error.flags_dict['cntCheck'] += 1

			return(Error,Parcel)
		except:
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with IMPROVED, LANDVALUE or CNTASSVALUE field. Please inspect the value of this field.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return(Error,Parcel)

	#checking taxparcelID and parcelID for redundancy
	def checkRedundantID(Error,Parcel,taxField,parcelField,acceptNull,errorType):
		nullList = ["<Null>", "<NULL>", "NULL", ""]
		try:
			taxIDToTest = getattr(Parcel,taxField)
			parcelIDToTest = getattr(Parcel,parcelField)
			#check redundancy; if none, continue
			if taxIDToTest is None and parcelIDToTest is None:
				pass

			elif taxIDToTest == parcelIDToTest:
				getattr(Parcel, errorType + "Errors").append("Redundant information in " + taxField.upper() + " and " + parcelField.upper() + " fields.")
				setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
				Error.flags_dict['redundantId'] += 1
			else:
				pass
			return (Error, Parcel)
		except:
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the " + taxField.upper() + "or" + parcelField.upper() + " fields. Please inspect the values of these fields.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	#Check for PROP/AUX value existing when expected and then check existing values for dups and for values not in expected domain lists...(Makes classOfPropCheck fcn obsolete)
	def auxPropCheck(Error,Parcel,propField,auxField,yearField,pinField,ignoreList,errorType,copDomainList,auxDomainList, acceptYears):
		nullList = ["<Null>", "<NULL>", "NULL", ""]
		try:
			year = getattr(Parcel,yearField)
			pinToTest = getattr(Parcel,pinField)
			copToTest = getattr(Parcel,propField)
			auxToTest = getattr(Parcel,auxField)
			testListCop = []
			testListAux = []
			if (pinToTest in ignoreList) or (pinToTest is None) or (year is not None and int(year) > int(acceptYears[1])):   #
				pass
			else:
				if copToTest is None and auxToTest is None:
					#print( str(year) + " and " + str(acceptYears[1]) )
					getattr(Parcel,errorType + "Errors").append("The " + propField.upper() + " and " + auxField.upper() + " fields are <Null> and a value is expected for any non-new parcels.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['auxPropCheck'] += 1

				if copToTest is not None and (copToTest in nullList or copToTest.isspace()):
						getattr(Parcel,errorType + "Errors").append("String values of #<Null>#; #NULL# or blanks occurred in " + propField.upper() + ". Please correct.")
						setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
						Error.badcharsCount  +=1   #for wrong <null> values

				elif copToTest is not None:
					checkVal = copToTest.split(",")
					for val in checkVal:
						if val.strip() not in copDomainList:
							getattr(Parcel,errorType + "Errors").append("A value provided in " + propField.upper() + " field is not in acceptable domain list.")
							setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
							Error.flags_dict['auxPropCheck'] += 1

						elif val.strip() in testListCop:
							getattr(Parcel,errorType + "Errors").append("Duplicate values exist in " + propField.upper() + " field.")
							setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
							Error.flags_dict['auxPropCheck'] += 1

						else:
							testListCop.append(val.strip())

				if auxToTest is not None and (auxToTest in nullList or auxToTest.isspace()):
						getattr(Parcel,errorType + "Errors").append("String values of #<Null>#; #NULL# or blanks occurred in " + auxField.upper() + ". Please correct.")
						setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
						Error.badcharsCount  +=1   #for wrong <null> values

				elif auxToTest is not None:
					checkAuxVal = auxToTest.split(",")
					for val in checkAuxVal:
						if val.strip() not in auxDomainList:
							getattr(Parcel,errorType + "Errors").append("A value provided in " + auxField.upper() + " field is not in AUXCLASS domain list. Standardize values for AUXCLASS domains.")
							setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
							Error.flags_dict['auxPropCheck'] += 1

						elif val.strip() in testListAux:
							getattr(Parcel,errorType + "Errors").append("Duplicate values exist in " + auxField.upper() + " field.")
							setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
							Error.flags_dict['auxPropCheck'] += 1

						else:
							testListAux.append(val.strip())
			return(Error, Parcel)
		except:
			getattr(Parcel,errorType + "Errors").append("!!!!!!An unknown issue occurred with the " + propField.upper() + " and/or " + auxField.upper() + " field. Please inspect the values of these fields.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	#checking ESTFMKVALUE field against PROPCLASS field for erroneous not null values when PROPCLASS of 4, 5, 5M or AUXCLASS field
	# for erroneous not null values when AUXCLASS of x1-x4 or w1-w9 is present with another value
	def fairMarketCheck(Error,Parcel,propClass,auxClass,estFmkValue,errorType):
		try:
			propClassTest = str(getattr(Parcel,propClass)).replace(" ","")
			auxClassValue = getattr(Parcel, auxClass)
			auxClassTest = str(getattr(Parcel,auxClass)).replace(" ","")
			estFmkValueTest = getattr(Parcel,estFmkValue)
			
			if (estFmkValueTest is None or float(estFmkValueTest) == 0 ) and auxClassValue is None and propClassTest is not None:
				if  re.search('4', propClassTest) is None and re.search('5', propClassTest) is None and (re.search('1', propClassTest) is not None or re.search('2', propClassTest) is not None or re.search('3', propClassTest) is not None or re.search('6', propClassTest) is not None or re.search('7', propClassTest) is not None):
					getattr(Parcel, errorType + "Errors").append("A value greater than zero is expected in ESTFMKVALUE for fully taxable properties with PROPCLASS of (" + str(propClassTest) + "). Verify value.")
					setattr(Error, errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['fairmarketCheck'] += 1
				else:
					pass
			#elif estFmkValueTest is not None:
				#if re.search('4', propClassTest) is not None or re.search('5', propClassTest) is not None:
				#	getattr(Parcel, errorType + "Errors").append("A <Null> value is expected in ESTFMKVALUE for properties with PROPCLASS values of 4, 5 and 5M. Correct or verify.")
				#	setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)

				#if re.search('W', auxClassTest) is not None or re.search('X', auxClassTest) is not None:
				#	getattr(Parcel, errorType + "Errors").append("A <Null> value is expected in ESTFMKVALUE for properties with AUXCLASS of (" + str(auxClassTest) + "). Verify value.")
				#	setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
				#else:
				#	pass
				return(Error,Parcel)
		except:
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the " + propClass.upper() + "  or  " + estFmkValue.upper() + " field. Please inspect the values of these fields.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	#checking CONAME, PARCELFIPS and PARCELSRC fields to ensure they match expected and meet domain requirements
	def matchContrib(Error,Parcel,coNamefield,fipsfield,srcfield,coNameDict,coNumberDict,acceptNull,errorType ):
		nullList = ["<Null>", "<NULL>", "NULL", " ", ""]
		try:
			coNameToTest = getattr(Parcel,coNamefield)
			fipsToTest = getattr(Parcel,fipsfield)
			srcToTest = getattr(Parcel,srcfield)
			if coNameToTest is not None:
				if coNameToTest in nullList or coNameToTest.isspace()  or any(x.islower() for x in coNameToTest):
					getattr(Parcel,errorType + "Errors").append("String values of #<Null>#; #NULL# or blanks occurred in " + coNamefield.upper() + ". Please correct.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.badcharsCount  +=1   #for wrong <null> values

					Error.coNameMiss += 1
					Error.flags_dict['matchContrib'] += 1
					Error.badcharsCount  +=1   #for wrong <null> values

				elif coNameToTest != Error.coName and (str(Error.coName) != 'OUTAGAMIE' and str( Error.coName) != 'WINNEBAGO' ): 
					getattr(Parcel,errorType + "Errors").append("The value provided in " + coNamefield.upper() + " field does not match expected county name.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['matchContrib'] += 1
					#Error.coNameMiss += 1

			else:
				if acceptNull:
					pass
				else:
					Error.coNameMiss += 1

			if fipsToTest is not None:
				if fipsToTest in nullList or fipsToTest.isspace()  or any(x.islower() for x in fipsToTest):
					getattr(Parcel,errorType + "Errors").append("String values of #<Null>#; #NULL# or blanks occurred in " + fipsfield.upper() + ". Please correct.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.fipsMiss += 1
					Error.flags_dict['matchContrib'] += 1
					Error.badcharsCount  +=1   #for wrong <null> values

				elif fipsToTest.upper() != coNameDict[Error.coName]:
					getattr(Parcel,errorType + "Errors").append("The value provided in " + fipsfield.upper() + " field does not match submitting county fips.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['matchContrib'] += 1
					#Error.fipsMiss += 1
			else:
				if acceptNull:
					pass
				else:
					Error.fipsMiss += 1
					#Error.flags_dict['matchContrib'] += 1

			if srcToTest is not None:
				if srcToTest in nullList or srcToTest.isspace()  or any(x.islower() for x in srcToTest):
					getattr(Parcel,errorType + "Errors").append("String values of #<Null>#; #NULL# or blanks occurred in " + srcfield.upper() + ". Please correct.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.srcMiss += 1
					Error.flags_dict['matchContrib'] += 1
					Error.badcharsCount  +=1   #for wrong <null> values

				elif srcToTest.upper() != coNumberDict[coNameDict[Error.coName]]:
					getattr(Parcel,errorType + "Errors").append("The value provided in " + srcfield.upper() + " field does not match submitting county name.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['matchContrib'] += 1
					#Error.srcMiss += 1

			else:
				if acceptNull:
					pass
				else:
					Error.srcMiss += 1
					#Error.flags_dict['matchContrib'] += 1
			return(Error,Parcel)
		except:
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the " + srcfield.upper() + " field. Please inspect the value of this field.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	#checking values provided in SCHOOLDISTNO and SCHOOLDIST field to ensure they are in our domain list and represent the same school dist (if both provided)
	def schoolDistCheck(Error,Parcel,pinField,schDistField,schDistNoField,schNoNameDict,schNameNoDict,errorType,ignoreList,yearField):
		nullList = ["<Null>", "<NULL>", "NULL", ""]
		try:
			schNo = getattr(Parcel,schDistNoField)
			schNa = getattr(Parcel,schDistField)
			pinToTest = getattr(Parcel,pinField)
			year = getattr(Parcel,yearField)
			if schNo is not None and schNa is not None:
				'''schNa = schNa.replace("SCHOOL DISTRICT", "").replace("SCHOOL DISTIRCT", "").replace("SCHOOL DIST","").replace("SCHOOL DIST.", "").replace("SCH DIST", "").replace("SCHOOL", "").replace("SCH D OF", "").replace("SCH", "").replace("SD", "").strip()'''
				try:
					if schNo != schNameNoDict[schNa] or schNa != schNoNameDict[schNo]:
						getattr(Parcel,errorType + "Errors").append("The values provided in " + schDistNoField.upper() + " and " + schDistField.upper() + " field do not match. Please verify values are in acceptable domain list.")
						setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
						Error.flags_dict['schoolDist'] += 1

				except:
					getattr(Parcel,errorType + "Errors").append("One or both of the values in the SCHOOLDISTNO field or SCHOOLDIST field are not in the acceptable domain list. Please verify values.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)

				return (Error,Parcel)
			if schNo is None and schNa is not None:
				'''schNa = schNa.replace("SCHOOL DISTRICT", "").replace("SCHOOL DISTIRCT", "").replace("SCHOOL DIST","").replace("SCHOOL DIST.", "").replace("SCH DIST", "").replace("SCHOOL", "").replace("SCH D OF", "").replace("SCH", "").replace("SD", "").strip()'''
				if schNa not in schNameNoDict:
					getattr(Parcel,errorType + "Errors").append("The value provided in " + schDistField.upper() + " is not within the acceptable domain list. Please verify value.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['schoolDist'] += 1

			if schNa is None and schNo is not None:
				if schNo not in schNoNameDict or len(schNo) != 4:
					getattr(Parcel,errorType + "Errors").append("The value provided in " + schDistNoField.upper() + " is not within the acceptable domain list or is not 4 digits long as expected. Please verify value.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['schoolDist'] += 1

			if schNo is None and schNa is None and pinToTest not in ignoreList and pinToTest is not None and (year is not None and int(year) <= 2018):
				getattr(Parcel,errorType + "Errors").append("Both the " + schDistNoField.upper() + " &  the " + schDistField.upper() + " are <Null> and a value is expected.")
				setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
				Error.flags_dict['schoolDist'] += 1

			return (Error,Parcel)
		except:
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the " + schDistField.upper() + " or " + schDistNoField.upper() + " field. Please inspect the values of these fields.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)

		return (Error, Parcel)

	def fieldCompleteness(Error,Parcel,fieldList,passList,CompDict):		
		for field in fieldList:
			if field.upper() in passList:
				pass
			else:
				stringToTest = getattr(Parcel,field.lower())
				if stringToTest is None:
					pass
				else:
					if stringToTest is not None or stringToTest != '':
						CompDict[field] = CompDict[field]+1
		return(Error,Parcel)

	def fieldCompletenessComparison(Error,fieldList,passList,currentStatDict,previousStatDict):
		for field in fieldList:
			if field.upper() in passList:
				pass
			else:
				if previousStatDict[field] > 0:
					Error.comparisonDict[field] = round((100*(currentStatDict[field] - previousStatDict[field])/ previousStatDict[field]),2)
				elif previousStatDict[field] == 0 and currentStatDict[field] == 0  :
					Error.comparisonDict[field] = 0.0
				elif  previousStatDict[field] == 0  :
					Error.comparisonDict[field] = 100.0
				#Error.comparisonDict[field] = round((100*(currentStatDict[field] - previousStatDict[field])/(Error.recordTotalCount)),2)
		return(Error)

	#checkSchemaFunction
	def checkSchema(Error, inFC,schemaType,fieldPassLst):
		realFieldList = []
		fieldDictNames = {}
		incorrectFields = []
		excessFields = []
		missingFields = []
		var = True

		#print("  Checking for all appropriate fields in " + str(inFc.GetName()) + "...\n")
		print("\n    Checking for all appropriate fields \n")

		### Get the description/definition of the layer i.e., feature class
		defn = inFC.GetLayerDefn()
		for i in range (defn.GetFieldCount()):
			code = defn.GetFieldDefn(i).GetType()
			fieldDictNames[defn.GetFieldDefn(i).GetName()] =[[defn.GetFieldDefn(i).GetFieldTypeName(code)], [defn.GetFieldDefn(i).GetWidth() ]]  #defn.GetFieldDefn(i).GetPrecision()
		
		i = 0
		while i  < defn.GetFieldCount():
			#if defn.GetFieldDefn(i).GetName() is not None: 
			if  str(defn.GetFieldDefn(i).GetName()) in ['GeneralElementErrors','AddressElementErrors','TaxrollElementErrors','GeometricElementErrors']:
					#print (defn.GetFieldDefn(i).GetName())
					inFC.DeleteField(i)
			else:
				i += 1
		#print ("=====>>>>\n")
		#print (fieldDictNames)	
		#print (schemaType)
		for field in fieldDictNames:
			if field.upper() not in fieldPassLst:
				if field not in schemaType.keys():
					excessFields.append(field)
					var = False
				
				elif fieldDictNames[field][0][0] not in schemaType[field][0] or fieldDictNames[field][1][0] not in schemaType[field][1]:
					incorrectFields.append(field)
					var = False
				else:
					missingFields = [i for i in schemaType.keys() if i not in fieldDictNames.keys()]
					if len(missingFields) > 0:
						var = False
		
		if var == False:
			print("\n  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
			print("     IMMEDIATE ERROR REQUIRING ATTENTION")
			print("\n  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
			print("  CERTAIN FIELDS DO NOT MEET THE PARCEL SCHEMA REQUIREMENTS.\n")
			if len(incorrectFields) > 0:
				# print("  THE PROBLEMATIC FIELDS INCLUDE: (" + str(incorrectFields).strip("[").strip("]").replace('u','') + ")\n")
				print("  ------->> PLEASE CHECK TO MAKE SURE THE NAMES, DATA TYPES, AND LENGTHS MATCH THE SCHEMA REQUIREMENTS.\n")
				pass
			if len(excessFields) > 0:
				# print("  THE EXCESS FIELDS INCLUDE: (" + str(excessFields).strip("[").strip("]").replace('u','') + ")\n")
				print("  ------->> PLEASE REMOVED FIELDS THAT ARE NOT IN THE PARCEL ATTRIBUTE SCHEMA.\n")
				pass
			if len(missingFields) > 0:
				# print("  THE MISSING FIELDS INCLUDE: (" + str(missingFields).strip("[").strip("]").replace('u','') + ")\n")
				print("  ------->> PLEASE ADD FIELDS THAT ARE NOT IN THE PARCEL ATTRIBUTE SCHEMA.\n")
				pass
			print("  PLEASE MAKE NEEDED ALTERATIONS TO THESE FIELDS AND RUN THE TOOL AGAIN.\n")
			# print("  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\n")
			#exit()
			sys.tracebacklimit = 0
			raise NameError("\n     PARCEL SCHEMA ERROR")
				
	#check for valid postal address   ('CANULL' not in address or 'NULL BLVD' not in address ) or
	def postalCheck (Error,Parcel,PostalAd,errorType,ignoreList,taxYear,pinField,badPstladdSet, acceptYears):
		nullList = ["<Null>", "<NULL>", "NULL", ""]
		try:
			address = getattr(Parcel,PostalAd)
			year = getattr(Parcel, taxYear)
			#print (str(year))
			#print ( str (acceptYears))
			pinToTest = getattr(Parcel,pinField)
			if address is None:
				pass
			else:

				if address in nullList or address.isspace():

					getattr(Parcel,errorType + "Errors").append("String values of #<Null>#; #NULL# or blanks occurred in " + PostalAd.upper() + ". Please correct.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['postalCheck'] += 1
					Error.badcharsCount  += 1   #for wrong <null> values

				elif year is not None:
					if int(year) <= int(acceptYears[1]):   #or pinToTest in ignorelist:
						if ('CANULL'  in address or 'NULL BLVD'  in address ):
							pass
						elif ('NOT AVAILABLE' in address or 'NONE PROVIDED' in address  or 'UNAVAILABLE' in address or 'ADDRESS' in address or 'ADDDRESS' in address or 'UNKNOWN' in address or ' 00000' in address or 'NULL' in address or  ('NONE' in address and 'HONONEGAH' not in address) or 'MAIL EXEMPT' in address or 'TAX EX' in address or 'UNASSIGNED' in address or 'N/A' in address) or(address in badPstladdSet) or  any(x.islower() for x in address):
							getattr(Parcel,errorType + "Errors").append("A value provided in the " + PostalAd.upper() + " field may contain an incomplete address. Please verify the value is correct or set to <Null> if complete address is unknown.")
							setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
							Error.flags_dict['postalCheck'] += 1
							#print (address)
						else:
							pass
			return(Error,Parcel)
		except:
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the PSTLADRESS field.  Please inspect the value of this field.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	#totError = Error.checkBadChars (totError )
	def checkBadChars(Error):
		if Error.badcharsCount >= 100:
			print("\n  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
			print("  THERE ARE AT LEAST 100 INSTANCES OF THE STRINGS '<Null>', \'NULL\', BLANKS AND/OR LOWER CASE CHARACTERS WITHIN THE ATTRIBUTE TABLE. \n")
			print("  RUN THE \"NULL FIELDS AND SET THE UPPERCASE TOOL\" AVAILABLE HERE: https://www.sco.wisc.edu/parcels/tools \n")
			print("  ONCE COMPLETE, RUN VALIDATION TOOL AGAIN.\n")
			print("  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\n")
			sys.tracebacklimit = 0
			raise NameError("\n     INSTANCES OF  '<Null>', \'NULL\', STRINGS IN FEATURE CLASS")
			#exit()

	def totalAssdValueCheck(Error,Parcel,cnt,lnd,imp,errorType):
		try:
			cnt = 0.0 if (getattr(Parcel,cnt) is None) else float(getattr(Parcel,cnt))
			lnd = 0.0 if (getattr(Parcel,lnd) is None) else float(getattr(Parcel,lnd))
			imp = 0.0 if (getattr(Parcel,imp) is None) else float(getattr(Parcel,imp))
			if lnd + imp != cnt:
				getattr(Parcel,errorType + "Errors").append("CNTASSDVALUE is not equal to LNDVALUE + IMPVALUE as expected.  Correct this issue and refer to the submission documentation for futher clarification as needed.")
				setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
				Error.flags_dict['cntCheck'] += 1
			return(Error,Parcel)
		except:
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred when comparing your CNTASSDVALUE value to the sum of LNDVALUE and IMPVALUE.  Please inspect these fields.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)

		return (Error, Parcel)

	# parcels with MFLValue should have auxclass of W1-W3 or W5-W9
	def mfLValueCheck(Error, Parcel, mflvalue, auxField, errorType):
		try:
			mflValueTest = getattr(Parcel,mflvalue)
			auxToTest = getattr(Parcel,auxField)

			if mflValueTest is None or float(mflValueTest) == 0.0:
				if auxToTest is not None and re.search('W', auxToTest) is not None and re.search('AW', auxToTest) is  None and re.search('W4', auxToTest) is  None and re.search('W10', auxToTest) is  None:
					getattr(Parcel, errorType + "Errors").append("A <Null> or zero value provided in MFLVALUE field does not match the (" + str(auxToTest) + ") AUXCLASS value(s). Refer to submission documentation for verification.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['mflvalueCheck'] += 1
			elif mflValueTest is not None and float(mflValueTest) > 0.0:
				if auxToTest is None:
					getattr(Parcel, errorType + "Errors").append("A <Null> value is expected in the MFLVALUE field according to the AUXCLASS field. Please verify.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['mflvalueCheck'] += 1
				elif re.search('W4', auxToTest) is not None:
					getattr(Parcel, errorType + "Errors").append("MFLVALUE does not include properties with AUXCLASS value of W4. Please verify.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['mflvalueCheck'] += 1
				elif re.search('AW', auxToTest) is not None:
					getattr(Parcel, errorType + "Errors").append("MFLVALUE does not include properties with AUXCLASS value of AWO/AW. Please verify.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['mflvalueCheck'] += 1
			else:
				pass
			return(Error, Parcel)
		except:
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the MFLVALUE field.  Please inspect the value of field.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	# checks that the mflvalue <> landvalue
	def mflLndValueCheck(Error,Parcel,parcelidfield, parcelidList,lnd,mfl,errorType):
		try:
			lnd = 0.0 if (getattr(Parcel,lnd) is None) else float(getattr(Parcel,lnd))
			mfl = 0.0 if (getattr(Parcel,mfl) is None) else float(getattr(Parcel,mfl))

			parcelid = getattr(Parcel, parcelidfield)

			if lnd == mfl and (lnd != 0.0 and mfl != 0.0):
				Error.mflLnd += 1
				if Error.mflLnd <= 10:
					parcelidList.append (parcelid) # need to save parcelid to add flag if necessary
				if Error.mflLnd > 10:
					getattr(Parcel,errorType + "Errors").append("MFLVALUE should not equal LNDVALUE in most cases.  Please correct this issue and refer to the submission documentation for further clarification as needed.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['mflvalueCheck'] += 1
			else:
				pass

			return(Error,Parcel)
		except:
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the MFLVALUE or LNDVALUE field.  Please inspect these fields.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	# checks that parcels with auxclass x1-x4  have taxroll values = <null>
	def auxclassFullyX4Check (Error,Parcel,auxclassField,propclassField,errorType):
		try:
			auxclass = getattr(Parcel,auxclassField)
			propclass = getattr(Parcel,propclassField)
			taxRollFields = {'IMPVALUE': getattr(Parcel, "impvalue"), 'CNTASSDVALUE': getattr(Parcel, "cntassdvalue"),
			'LNDVALUE': getattr(Parcel, "lndvalue"), 'MFLVALUE': getattr(Parcel, "mflvalue"),
			'ESTFMKVALUE': getattr(Parcel, "estfmkvalue"),
			'NETPRPTA': getattr(Parcel, "netprpta"), 'GRSPRPTA': getattr(Parcel, "grsprpta")}

			probFields = []
			if auxclass is not None:
				if auxclass == 'X4' and propclass is None:					
					for key, val in taxRollFields.items():    #iteritems():
						if val is not None:
							probFields.append(key)
					if len(probFields) > 0:
						getattr(Parcel,errorType + "Errors").append("A <Null> value is expected in " + " / ".join(probFields) + "  for properties with AUXCLASS of X4. Please correct.")
						setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
						Error.flags_dict['auxclassFullyX4'] += 1

				else:  #W values are okay
					pass
				return (Error, Parcel)

		except: # using generic error handling because we don't know what errors to expect yet.
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the " + auxclassField.upper() + " field. Please inspect the value of this field.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)

		return (Error, Parcel)

	# checks that parcels with auxclass x1-x4  have taxroll values = <null>
	def auxclassTaxrollCheck (Error,Parcel,auxclassField,errorType):
		try:
			auxclass = getattr(Parcel,auxclassField)
			taxRollFields = {'IMPVALUE': getattr(Parcel, "impvalue"), 'CNTASSDVALUE': getattr(Parcel, "cntassdvalue"),
			'LNDVALUE': getattr(Parcel, "lndvalue"), 'MFLVALUE': getattr(Parcel, "mflvalue"),
			'ESTFMKVALUE': getattr(Parcel, "estfmkvalue"),
			'NETPRPTA': getattr(Parcel, "netprpta"), 'GRSPRPTA': getattr(Parcel, "grsprpta")}

			taxFields = []
			if auxclass is not None:
				if re.search('X', auxclass) is not None:
					for key, val in taxRollFields.iteritems():
						if val is not None:
							taxFields.append(key)
					if len(taxFields) > 0:
						getattr(Parcel,errorType + "Errors").append("A <Null> value is expected in " + " / ".join(taxFields) + "  for properties with AUXCLASS of (" + str(auxclass) + "). Please correct.")
						setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
				else:  #W values are okay
					pass
				return (Error, Parcel)

		except: # using generic error handling because we don't know what errors to expect yet.
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the AUXCLASS field. Please inspect the value of this field.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	# check that propclass, net and gross with 0.0 or <Null> do not have propclass value
	def propClassCntCheck (Error,Parcel,propClass,auxClass, taxRollValue,errorType):
		nullList = ["<Null>", "<NULL>", "NULL", ""]
		try:
			propClassTest = getattr(Parcel,propClass)
			auxClassTest = getattr(Parcel, auxClass)
			cnt = getattr(Parcel, taxRollValue)
			if cnt is None or float(cnt) == 0:
				if auxClassTest is not None and re.search ('AW', str(auxClassTest)):
					pass    ## Calumet case
				elif (re.search('1', str(propClassTest)) or re.search('2', str(propClassTest)) or re.search('3',str(propClassTest)) or re.search('4', str(propClassTest)) or re.search('5',str(propClassTest)) or re.search('6',str(propClassTest)) or re.search('7',str(propClassTest))):
					getattr(Parcel, errorType + "Errors").append("A value greater than zero is expected in " + taxRollValue.upper() + " for properties with PROPCLASS of (" + str(propClassTest) + "). Verify value.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['cntPropClassCheck'] += 1
				else:
					pass
			elif cnt is not None and float(cnt) > 0:
				if propClassTest is None:
					getattr(Parcel, errorType + "Errors").append("The value provided in " + taxRollValue.upper() + " does not correspond with PROPCLASS value(s) of (" + str(propClassTest) + "). Please verify.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.flags_dict['cntPropClassCheck'] += 1

		except:
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the " + taxRollValue.upper() + " field.  Please inspect the <Null> value provided in PROPCLASS.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	def propClassNetGrosCheck (Error,Parcel,propClass,auxClass, netValue, grosValue, errorType):
		nullList = ["<Null>", "<NULL>", "NULL", ""]
		try:
			taxRollFields = {'NETPRPTA': getattr(Parcel, "netprpta"), 'GRSPRPTA': getattr(Parcel, "grsprpta")}
			propClassTest = getattr(Parcel,propClass)
			auxClassTest = getattr(Parcel, auxClass)
			net = getattr(Parcel, netValue)
			gros = getattr(Parcel, grosValue)
			if (net is None or float(net) == 0) and (gros is None or float(gros) == 0):
				if auxClassTest is not None and re.search ('AW', str(auxClassTest)):
					pass    ## Calumet case

				elif (re.search('1', str(propClassTest)) or re.search('2', str(propClassTest)) or re.search('3',str(propClassTest)) or re.search('4', str(propClassTest)) or re.search('5',str(propClassTest)) or re.search('6',str(propClassTest)) or re.search('7',str(propClassTest))):
					getattr(Parcel, errorType + "Errors").append("A value greater than zero is expected in NETPRPTA/GRSPRPTA for properties with PROPCLASS of (" + str(propClassTest) + "). Verify value.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					#Error.flags_dict['cntPropClassCheck'] += 1
				else:
					pass
			elif (net is not None and float(net) > 0) or (gros is not None and float(gros) > 0)  :
				if propClassTest is None:
					getattr(Parcel, errorType + "Errors").append("The value provided in NETPRPTA/GRSPRPTA does not correspond with PROPCLASS value(s) of (" + str(propClassTest) + "). Please verify.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					#Error.flags_dict['cntPropClassCheck'] += 1

		except:
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the NETPRPTA/GRSPRPTA field(s).  Please inspect the <Null> value provided in PROPCLASS.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	#check for instances of net > gross
	def netVsGross(Error,Parcel,netField,grsField,errorType):
		try:
			netIn = getattr(Parcel,netField)
			grsIn = getattr(Parcel,grsField)
			if netIn is not None and grsIn is not None:
				if float(grsIn) >= float(netIn):
					pass
				else:
					getattr(Parcel,errorType + "Errors").append("The NETPRPTA value is greater than the GRSPRPTA value.  See Submission_Documentation.pdf for verification.")
					setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
					Error.netMoreGrsCnt += 1
					#Error.flags_dict['netvsGross'] += 1
				return (Error,Parcel)
			else:
				pass
			return (Error, Parcel)
		except:
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the NETPRPTA or GRSPRPTA field.  Please inspect the values of these fields.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	# What does this function do?
	# def checkCodedDomains(Error,featureClass):
	#	return Error

	#backup geom check function for 100 no parcelid matches...
	def ctyExtentCentCheck(self, infc, centroidDict):
		coname = self.coName
		print ('   in centroid function')
	
		xMin, xMax, yMin, yMax = infc.GetExtent()
		iNxMid = xMin + ((xMax - xMin)/2)
		iNyMid = yMin + ((yMax - yMin)/2)

		if (centroidDict[coname][0] - 100) <= round(iNxMid,0) <= (centroidDict[coname][0] + 100) and (centroidDict[coname][1] - 100) <= round(iNyMid,0) <= (centroidDict[coname][1] + 100):
			print("  THE GEOMETRY OF THIS FEATURE CLASS WAS VALIDATED.  \n")
		else:
			print("\n  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
			print("  THE GEOMETRY OF THIS FEATURE CLASS WAS NOT VALIDATED.  \n")
			# print("  THIS ISSUE CAN BE INDICATIVE OF A RE-PROJECTION ERROR. \n ")
			# print("  REMINDER: YOUR DATA SHOULD BE RE-PROJECTED TO NAD_1983_HARN_Wisconsin_TM (Meters) PRIOR TO LOADING DATA INTO THE TEMPLATE FEATURE CLASS.\n")
			# print("  PLEASE MAKE NEEDED ALTERATIONS TO THE FEATURE CLASS AND RUN THE TOOL AGAIN.\n")
			print("  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\n")
			sys.tracebacklimit = 0
			raise NameError("\n     GEOMETRY OF FEATURE CLASS NOT VALIDATED")
			#exit()
 

	#checking strings for unacceptable chars including /n, /r, etc...
	def badChars(Error,Parcel,fieldNamesList,charDict,errorType):
		try:
			for f in fieldNamesList:
				if f in charDict:
					testRegex = str(charDict[f]).replace(",",'').replace("'","").replace('"','').replace(" ","")
					stringToTest = str(getattr(Parcel,f.lower()))
					if stringToTest is not None:
						if re.search(testRegex,stringToTest) is not None:
							getattr(Parcel,errorType + "Errors").append("Bad characters found in " + f.upper())
							setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
			return (Error, Parcel)
		except:
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the " + f.upper() + " field. Please inspect the value of this field.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	#checking strings for unacceptable chars including /n, /r, etc...
	def reallyBadChars(Error,Parcel,fieldNamesList,charDict,errorType):
		# print("  Testing reallyBadChars()")
		# print("  " + str(getattr(Parcel,"ownernme1"))) # The most explicit way of accessing an attribute on parcel. We use the below example as a way of making the functions more flexible - with this strategy, they can test different character lists against different fields.
		# print("  " + str(getattr(Parcel,fieldNamesList[7].lower()))) # externalDicts.py/fieldNames is passed as fieldNamesList for this function (ownername1 is in the 8th position)
		# print("  " + str(Parcel.ownernme1)) # The another explicit way of accessing an attribute on parcel
		try:
			for f in fieldNamesList:
				#print(str(getattr(Parcel,f.lower()))) # similar to the above, access the attribute value of the fieldname "f"
				if f in charDict:
					testRegex = str(charDict[f]).replace(",",'').replace("'","").replace('"','').replace(" ","")
					stringToTest = str(getattr(Parcel,f.lower()))
					if stringToTest is not None:
						if re.search(testRegex,stringToTest) is not None:
							getattr(Parcel,errorType + "Errors").append("Bad characters found in " + f.upper())
							setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
			return (Error, Parcel)
		except:
			getattr(Parcel,errorType + "Errors").append("An unknown issue occurred with the " + f.upper() + " field. Please inspect the value of this field.")
			setattr(Error,errorType + "ErrorCount", getattr(Error,errorType + "ErrorCount") + 1)
		return (Error, Parcel)

	@staticmethod

	def versionCheck(inVersion):
		# try:
		currVersion = urllib.request.urlopen('http://www.sco.wisc.edu/parcels/tools/Validation/validation_version.txt').read().decode("utf8")
		# print(  inVersion)
		if inVersion == currVersion:
			print("\n    Tool up to date.\n\n")
			#print("    "+ str(inVersion) + "\n")
		else:
			#exit()
			sys.tracebacklimit = 0
			raise NameError("\n     TOOL VERSION ERROR")

		# except Exception:
			# print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
			# print("Check the change log at http://www.sco.wisc.edu/parcels/tools/")
			# print("to make sure the latest version of the tool is installed before submitting")


	@staticmethod

	def loadParcelData(  ):
		"""load parcel data from website"""
		# try:
		data = urllib.request.urlopen('http://www.sco.wisc.edu/parcels/tools/Validation/parcelsData.txt')
		# print(  inVersion)

		dataList = []
		for lines in data.readlines():
			dataList.append(lines.decode("utf8"))
	
		#pinSkips, taxRollYears, prefixDomains, suffixDomains, streetTypes, unitType, unitId, badPstladdSet, stNameDict

		return dataList 
