'''This file contains the lengthy dictionaries used by the validation tool script'''

#list of field names 
fieldNames = ["OID@","SHAPE@","STATEID","PARCELID","TAXPARCELID","PARCELDATE","TAXROLLYEAR",
"OWNERNME1","OWNERNME2","PSTLADRESS","SITEADRESS","ADDNUMPREFIX","ADDNUM","ADDNUMSUFFIX","PREFIX","STREETNAME",
"STREETTYPE","SUFFIX","LANDMARKNAME","UNITTYPE","UNITID","PLACENAME","ZIPCODE","ZIP4","STATE","SCHOOLDIST",
"SCHOOLDISTNO","IMPROVED","CNTASSDVALUE","LNDVALUE","IMPVALUE","FORESTVALUE","ESTFMKVALUE","NETPRPTA","GRSPRPTA",
"PROPCLASS","AUXCLASS","ASSDACRES","DEEDACRES","GISACRES","CONAME","LOADDATE","PARCELFIPS","PARCELSRC",
"SHAPE@LENGTH","SHAPE@AREA","SHAPE@XY","GeneralElementErrors","AddressElementErrors","TaxrollElementErrors","GeometricElementErrors"]

fieldListPass = ["OID","OID@","SHAPE","SHAPE@","SHAPE_LENGTH","SHAPE_AREA","SHAPE_XY","SHAPE@LENGTH","SHAPE@AREA","SHAPE@XY","LONGITUDE","LATITUDE","GENERALELEMENTERRORS","ADDRESSELEMENTERRORS","TAXROLLELEMENTERRORS","GEOMETRICELEMENTERRORS"]

#V3 schema requirements
schemaReq = {
	'STATEID':[['String'],[100]],
	'PARCELID':[['String'],[100]],
	'TAXPARCELID':[['String'],[100]],
	'PARCELDATE':[['String'],[25]],
	'TAXROLLYEAR':[['String'],[10]],
	'OWNERNME1':[['String'],[254]],
	'OWNERNME2':[['String'],[254]],
	'PSTLADRESS':[['String'],[200]],
	'SITEADRESS':[['String'],[200]],
	'ADDNUMPREFIX':[['String'],[50]],
	'ADDNUM':[['String'],[50]],
	'ADDNUMSUFFIX':[['String'],[50]],
	'PREFIX':[['String'],[50]],
	'STREETNAME':[['String'],[50]],
	'STREETTYPE':[['String'],[50]],
	'SUFFIX':[['String'],[50]],
	'LANDMARKNAME':[['String'],[50]],
	'UNITTYPE':[['String'],[50]],
	'UNITID':[['String'],[50]],
	'PLACENAME':[['String'],[100]],
	'ZIPCODE':[['String'],[50]],
	'ZIP4':[['String'],[50]],
	'STATE':[['String'],[50]],
	'SCHOOLDIST':[['String'],[50]],
	'SCHOOLDISTNO':[['String'],[50]],
	'IMPROVED':[['String'],[10]],
	'CNTASSDVALUE':[['String','Double'],[50,8]],
	'LNDVALUE':[['String','Double'],[50,8]],
	'IMPVALUE':[['String','Double'],[50,8]],
	'FORESTVALUE':[['String','Double'],[50,8]],
	'ESTFMKVALUE':[['String','Double'],[50,8]],
	'NETPRPTA':[['String','Double'],[50,8]],
	'GRSPRPTA':[['String','Double'],[50,8]],
	'PROPCLASS':[['String'],[150]],
	'AUXCLASS':[['String'],[150]],
	'ASSDACRES':[['String','Double'],[50,8]],
	'DEEDACRES':[['String','Double'],[50,8]],
	'GISACRES':[['String','Double'],[50,8]],
	'CONAME':[['String'],[50]],
	'LOADDATE':[['String'],[10]],
	'PARCELFIPS':[['String'],[10]],
	'PARCELSRC':[['String'],[50]],
}

#bad characters dictionary
fieldNamesBadChars = {
"PARCELID": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")"],
"TAXPARCELID": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")"],
"PARCELDATE": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\-"],
"TAXROLLYEAR": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',"\-"],
"OWNERNME1": ["\n","\r"],
"OWNERNME2": ["\n","\r"],
"PSTLADRESS": ["\n","\r"],
"SITEADRESS": ["\n","\r"],
"ADDNUMPREFIX": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',','.',"\-"],
"ADDNUM": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',','.',"\-"],
"ADDNUMSUFFIX": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~",',','.'],
"PREFIX": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',','.',"\-"],
"STREETNAME": ["\n","\r","$","^","=","<",">","@","#","%","?","!","*","~","(",")"],
"STREETTYPE": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',','.',"\-"],
"SUFFIX": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',','.',"\-"],
"LANDMARKNAME": ["\n","\r"],
"UNITTYPE": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',','.',"\-"],
"UNITID": ["\n","\r","$","^","=","<",">","@","%","?","`","!","*","~","(",")",','],
"PLACENAME": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',',"\-"],
"ZIPCODE": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',','.',"\-"],
"ZIP4": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',','.',"\-"],
"STATE": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',','.',"\-"],
"SCHOOLDIST": ["\n","\r","$","^","=","<",">","@","#","%","&","?","!","*","~","(",")","\\",'/',','],
"SCHOOLDISTNO": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',','.',"\-"],
"IMPROVED": ["\n","\r","$","^","=","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',','.',"\-"],
"CNTASSDVALUE": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',',"\-"],
"LNDVALUE": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',',"\-"],
"IMPVALUE": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',',"\-"],
"FORESTVALUE": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',',"\-"],
"ESTFMKVALUE": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',',"\-"],
"NETPRPTA": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',',"\-"],
"GRSPRPTA": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',',"\-"],
"PROPCLASS": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/','.',"\-"],
"AUXCLASS": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/','.',"\-"],
"ASSDACRES": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',',"\-"],
"DEEDACRES": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',',"\-"],
"GISACRES": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',','],
"CONAME": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',',"\-"],
"LOADDATE": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")",',','.','\-'],
"PARCELFIPS": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',','.',"\-"],
"PARCELSRC": ["\n","\r","$","^","=","<",">","@","#","%","&","?","`","!","*","~","(",")","\\",'/',',','.',"\-"]
}

#acceptable COP domains
copDomains = ['1','2','3','4','5','6','7','5M','M']

#acceptable AUXCOP domains
auxDomins = ['W1','W2','W3','W4','W5','W6','W7','W8','X1','X2','X3','X4','M']

#dictionary for V3 completeness collection
v3CompDict = {
	'STATEID':0,
	'PARCELID':0,
	'TAXPARCELID':0,
	'PARCELDATE':0,
	'TAXROLLYEAR':0,
	'OWNERNME1':0,
	'OWNERNME2':0,
	'PSTLADRESS':0,
	'SITEADRESS':0,
	'ADDNUMPREFIX':0,
	'ADDNUM':0,
	'ADDNUMSUFFIX':0,
	'PREFIX':0,
	'STREETNAME':0,
	'STREETTYPE':0,
	'SUFFIX':0,
	'LANDMARKNAME':0,
	'UNITTYPE':0,
	'UNITID':0,
	'PLACENAME':0,
	'ZIPCODE':0,
	'ZIP4':0,
	'STATE':0,
	'SCHOOLDIST':0,
	'SCHOOLDISTNO':0,
	'IMPROVED':0,
	'CNTASSDVALUE':0,
	'LNDVALUE':0,
	'IMPVALUE':0,
	'FORESTVALUE':0,
	'ESTFMKVALUE':0,
	'NETPRPTA':0,
	'GRSPRPTA':0,
	'PROPCLASS':0,
	'AUXCLASS':0,
	'ASSDACRES':0,
	'DEEDACRES':0,
	'GISACRES':0,
	'CONAME':0,
	'LOADDATE':0,
	'PARCELFIPS':0,
	'PARCELSRC':0,
}