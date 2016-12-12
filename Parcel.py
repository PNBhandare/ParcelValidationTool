import arcpy
#TODO:
# 1) change the structure of the row to be fieldNames index (e.g. fieldNames.index("GeneralElementErrors")])
# 2) ...

#Parcel class defines a parcel record based on the attribute schema
class Parcel:
	#Class vars go here

	#Initialize a parcel object
	def __init__(self,row,fieldNames):
		self.objectid = row[fieldNames.index("OID@")]
		self.shape = row[fieldNames.index("SHAPE@")]
		self.stateid = row[fieldNames.index("STATEID")]
		self.parcelid = row[fieldNames.index("PARCELID")]
		self.taxparcelid = row[fieldNames.index("TAXPARCELID")]
		self.parceldate = row[fieldNames.index("PARCELDATE")]
		self.taxrollyear = row[fieldNames.index("TAXROLLYEAR")]
		self.ownername1 = row[fieldNames.index("OWNERNME1")]
		self.ownername2 = row[fieldNames.index("OWNERNME2")]
		self.mailadd = row[fieldNames.index("PSTLADRESS")]
		self.siteadd = row[fieldNames.index("SITEADRESS")]
		self.addnumprefix = row[fieldNames.index("ADDNUMPREFIX")]
		self.addnum = row[fieldNames.index("ADDNUM")]
		self.addnumsuffix = row[fieldNames.index("ADDNUMSUFFIX")]
		self.prefix = row[fieldNames.index("PREFIX")]
		self.streetname = row[fieldNames.index("STREETNAME")]
		self.streettype = row[fieldNames.index("STREETTYPE")]
		self.suffix = row[fieldNames.index("SUFFIX")]
		self.landmarkname = row[fieldNames.index("LANDMARKNAME")]
		self.unittype = row[fieldNames.index("UNITTYPE")]
		self.unitid = row[fieldNames.index("UNITID")]
		self.placename = row[fieldNames.index("PLACENAME")]
		self.zipcode = row[fieldNames.index("ZIPCODE")]
		self.zip4 = row[fieldNames.index("ZIP4")]
		self.state = row[fieldNames.index("STATE")]
		self.schooldist = row[fieldNames.index("SCHOOLDIST")]
		self.schooldistno = row[fieldNames.index("SCHOOLDISTNO")]
		self.improved = row[fieldNames.index("IMPROVED")]
		self.cntassdvalue = row[fieldNames.index("CNTASSDVALUE")]
		self.lndvalue = row[fieldNames.index("LNDVALUE")]
		self.impvalue = row[fieldNames.index("IMPVALUE")]
		self.forestvalue = row[fieldNames.index("FORESTVALUE")]
		self.estfmkvalue = row[fieldNames.index("ESTFMKVALUE")]
		self.netprpta = row[fieldNames.index("NETPRPTA")]
		self.grsprpta = row[fieldNames.index("GRSPRPTA")]
		self.propclass = row[fieldNames.index("PROPCLASS")]
		self.auxclass = row[fieldNames.index("AUXCLASS")]
		self.assdacres = row[fieldNames.index("ASSDACRES")]
		self.deedacres = row[fieldNames.index("DEEDACRES")]
		self.gisacres = row[fieldNames.index("GISACRES")]
		self.coname = row[fieldNames.index("CONAME")]
		self.loaddate = row[fieldNames.index("LOADDATE")]
		self.parcelfips = row[fieldNames.index("PARCELFIPS")]
		self.parcelsrc = row[fieldNames.index("PARCELSRC")]
		self.shapeLength = row[fieldNames.index("SHAPE@LENGTH")]
		self.shapeArea = row[fieldNames.index("SHAPE@AREA")]
		self.geomErrors = []
		self.addressErrors = []
		self.taxErrors = []
		self.genErrors = []
		
	def writeErrors(self, row, cursor, fieldNames):
		arcpy.AddMessage(self.addressErrors)
		arcpy.AddMessage(self.addressErrors)
		# create 
		if len(self.addressErrors) > 0:
			row[fieldNames.index("AddressElementErrors")] = str(self.addressErrors).strip('[]').replace("'","")
		if len(self.genErrors) > 0:
			row[fieldNames.index("GeneralElementErrors")] = str(self.genErrors).strip('[]').replace("'","")
		if len(self.taxErrors) > 0:
			row[fieldNames.index("TaxrollElementErrors")] = str(self.taxErrors).strip('[]').replace("'","")
		if len(self.geomErrors) > 0:
			row[fieldNames.index("GeometricElementErrors")] = str(self.geomErrors).strip('[]').replace("'","")
		#row[47] = "currParcel.addressErrors"
		cursor.updateRow(row)

	#def __getitem__(self, key):
	#	return self[key]
