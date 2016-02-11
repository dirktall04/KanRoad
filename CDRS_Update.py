'''
Created on Sep 26, 2013
udpated on Oct 10, 2013
@author: kyleg
Modified by Dirk 2015-09-08
'''


try:
	from config import sdeCDRS, sdeCDRSWZ, sdeWichwayCDRS, metadataFolder # @UnresolvedImport
except:
	print "Import Error on Config file, setting the parameters"
	sdeCDRS = r"D:\wichway\harvesters\python\KRProd.sde\KANROAD.CDRS_ALERT_ROUTE"
	sdeCDRSWZ = r"D:\wichway\harvesters\python\KRProd.sde\KANROAD.CDRS_WZ_DETAIL"
	sdeWichwayCDRS = r"D:\wichway\harvesters\python\wichway_spatial.sde\wichway_spatial.WICHWAY_SPATIAL.CDRS_LAM"
	metadataFolder = r"D:\TEMP\Metadata"


import os
import sys
import datetime
starttime = (datetime.datetime.now()) 
print str(starttime) + " starting script"
#import arcpy functions utilized in this script
from arcpy import (MakeQueryTable_management, DeleteRows_management, DefineProjection_management, TableToTable_conversion, 
				Append_management, TruncateTable_management, AddJoin_management, CalculateField_management, 
				MakeFeatureLayer_management, env, FeatureClassToFeatureClass_conversion, AddField_management, 
				ClearWorkspaceCache_management, Exists, MetadataImporter_conversion, XSLTransform_conversion, Delete_management,
				CopyFeatures_management, RemoveJoin_management)
from arcpy.da import (InsertCursor as daInsertCursor, SearchCursor as daSearchCursor)  # @UnresolvedImport


#print str(datetime.datetime.now()) + " setting global variables"
env.overwriteOutput= True
lambertCC = "PROJCS['NAD_83_Kansas_Lambert_Conformal_Conic_Meters',GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Lambert_Conformal_Conic'],PARAMETER['false_easting',0.0],PARAMETER['false_northing',0.0],PARAMETER['central_meridian',-98.0],PARAMETER['standard_parallel_1',38.0],PARAMETER['standard_parallel_2',39.0],PARAMETER['scale_factor',1.0],PARAMETER['latitude_of_origin',38.5],UNIT['Meter',1.0]]"
stagews = "in_memory"


def RemoveGpHistory_fc(out_xml):
	###remove_gp_history_xslt = r"D:\Program Files (x86)\ArcGIS\Desktop10.2\Metadata\Stylesheets\gpTools\remove geoprocessing history.xslt"
	remove_gp_history_xslt = r"C:\GIS\KanRoadTesting\remove geoprocessing history.xslt"
	env.workspace = out_xml
	ClearWorkspaceCache_management()
	if Exists(out_xml):
		Delete_management(out_xml,"Folder")
		#print 'folder deleted'
	from os import mkdir
	mkdir(out_xml)
	#print 'metadata folder created'
	
	try:
		name_xml = "CDRS_LAM.xml"
		#Process: XSLT Transformation
		XSLTransform_conversion(sdeWichwayCDRS, remove_gp_history_xslt, name_xml, "")
		#print "Completed xml conversion on {0}".format(sdeWichwayCDRS)
		# Process: Metadata Importer
		MetadataImporter_conversion(name_xml,sdeWichwayCDRS)
		#print "Imported XML on {0}".format(sdeWichwayCDRS)
	except:
		print "could not complete xml conversion on {0}".format(sdeWichwayCDRS)
		pass


def TnA():
	try:
		env.workspace = stagews
		#copying oracle tables to memory
		print str(datetime.datetime.now()) + ' copying oracle tables to memory'
		FeatureClassToFeatureClass_conversion(sdeCDRS,"in_memory","Construction","#","ALERT_STATUS <>  3")
		MakeQueryTable_management(sdeCDRSWZ,"wz1","USE_KEY_FIELDS","KANROAD.CDRS_WZ_DETAIL.CDRS_WZ_DETAIL_ID",
								"""KANROAD.CDRS_WZ_DETAIL.CDRS_WZ_DETAIL_ID #;KANROAD.CDRS_WZ_DETAIL.CDRS_DETOUR_TYPE_ID #;
								KANROAD.CDRS_WZ_DETAIL.WORK_ZONE_DESC #;KANROAD.CDRS_WZ_DETAIL.WORK_ZONE_SPEED_RESTRIC #;
								KANROAD.CDRS_WZ_DETAIL.DETOUR_TYPE_TXT #;KANROAD.CDRS_WZ_DETAIL.DETOUR_SPEED_RESTRIC #;
								KANROAD.CDRS_WZ_DETAIL.DETOUR_DESC #""", "#")
		TableToTable_conversion("wz1", 'in_memory', 'wz')
		#Joining the Oracle CDRS WZ table
		print str(datetime.datetime.now()) + " Joining the Oracle CDRS WZ table"
		MakeFeatureLayer_management("Construction", "ConstJoin")
		AddJoin_management("ConstJoin","CDRS_WZ_DETAIL_ID","wz","KANROAD_CDRS_WZ_DETAIL_CDRS_WZ_DETAIL_ID","KEEP_ALL")
		FeatureClassToFeatureClass_conversion("ConstJoin","in_memory","CDRS","#",'ConstJoin.ALERT_STATUS <  3', "#")
		#reformatting the Route name for US routes
		print str(datetime.datetime.now()) + " reformatting the Route name for US routes"
		AddField_management("CDRS", "RouteName", "TEXT", "#", "10")
		routenamed = '!Construction_BEG_LRS_ROUTE![0:1] +str(!Construction_BEG_LRS_ROUTE![3:6]).lstrip("0")'  # calculation expression
		#Calculate the Route names for User Display
		print routenamed
		CalculateField_management("CDRS", "RouteName", routenamed, "PYTHON_9.3","#") 
		AddField_management("CDRS", "STATUS", "TEXT", "#", "10")
		AddField_management("CDRS", "Alert_Status_I", "LONG", "#", "#")
		CalculateField_management("CDRS", "Alert_Status_I", '!Construction_ALERT_STATUS!' , "PYTHON_9.3", "#") 
		#Assigning projection for KanRoad CDRS Alert Route Layer
		print str(datetime.datetime.now()) + "Assigning projection for KanRoad CDRS Alert Route Layer"
		DefineProjection_management("CDRS", lambertCC)
		#reformatting the Route name for US routes
		print str(datetime.datetime.now()) + " reformatting the Route name for US routes"
		MakeFeatureLayer_management("CDRS", "ACTIVERoutes", '"Construction_ALERT_STATUS" =  2' )
		CalculateField_management("ACTIVERoutes","STATUS",'"Active"',"PYTHON_9.3","#") 
		
		MakeFeatureLayer_management("CDRS", "ClosedRoutes", '"Construction_ALERT_STATUS" =  2 AND "Construction_FEA_CLOSED" =  1')
		CalculateField_management("ClosedRoutes","STATUS",'"Closed"',"PYTHON_9.3","#") 
		
		MakeFeatureLayer_management("CDRS", "PlannedRoutes", '"Construction_ALERT_STATUS" =  1' )
		CalculateField_management("PlannedRoutes","STATUS",'"Planned"',"PYTHON_9.3","#")
		
		#copying joined oracle tables to memory for loading in Wichway Schema
		print str(datetime.datetime.now()) + " copying joined oracle tables to memory for loading in Wichway Schema"
		FeatureClassToFeatureClass_conversion(sdeWichwayCDRS, "in_memory", "CDRS_Segments", "#", "#")
		
		#delete rows in the destination feature class
		DeleteRows_management("CDRS_Segments")
		
		###############################################################################################################
		# Maintainability information:
		# If you need to add another field to transfer between the two, just add it to the searchCursorFields and the
		# insertCursorFields lists and make sure that it is in the same position in the list order for both of
		# them.
		# Besides 'LoadDate', the order does not matter, so long as each field name in the
		# searchCursorFields has a counterpart in the insertCursorFields and vice versa.
		# 'LoadDate' should always be last for the insertCursorFields as it is appended to each row after all
		# of the other items from the searchCursorFields.
		###############################################################################################################
		
		featuresToTransfer = list()
		
		# searchCursorFields go to "in_memory\CDRS". (Input table)
		searchCursorFields = ['SHAPE@', 'RouteName', 'Construction_BEG_STATE_LOGMILE', 'Construction_END_STATE_LOGMILE', 'Construction_BEG_COUNTY_NAME', 
							'Construction_ALERT_DATE', 'Construction_COMP_DATE', 'Construction_ALERT_TYPE_TXT', 'Construction_ALERT_DESC_TXT',
							'Construction_VERT_RESTRICTION', 'Construction_WIDTH_RESTRICTION', 'Construction_TIME_DELAY_TXT',
							'Construction_PUBLIC_COMMENT', 'wz_KANROAD_CDRS_WZ_DETAIL_DETOUR_TYPE_TXT',
							'wz_KANROAD_CDRS_WZ_DETAIL_DETOUR_DESC', 'Construction_CONTACT_NAME', 'Construction_CONTACT_PHONE', 
							'Construction_CONTACT_EMAIL', 'Construction_ALERT_HYPERLINK',  'Alert_Status_I',
							'Construction_FEA_CLOSED', 'STATUS', 'Construction_ALERT_DIREC_TXT', 'Construction_BEG_LONGITUDE',
							'Construction_BEG_LATITUDE']
		
		# insertCursorFields go to sdeWichwayCDRS. (Output table)
		insertCursorFields = ['SHAPE@', 'RouteName', 'BeginMP', 'EndMP', 'County', 'StartDate', 'CompDate', 'AlertType', 'AlertDescription',
							'HeightLimit', 'WidthLimit', 'TimeDelay', 'Comments', 'DetourType', 'DetourDescription',
							'ContactName', 'ContactPhone', 'ContactEmail', 'WebLink',  'AlertStatus', 'FeaClosed', 'Status',
							'AlertDirectTxt', 'X', 'Y', 'LoadDate']
		
		cdrsSearchCursor = daSearchCursor(r"in_memory\CDRS", searchCursorFields)
		
		for cdrsCursorItem in cdrsSearchCursor:
			featureItem = list(cdrsCursorItem)
			featureItem.append(starttime)
			featuresToTransfer.append(featureItem)
		
		RemoveJoin_management("ConstJoin", "wz")
		
		#truncating CDRS segments in WICHWAY SPATIAL
		print str(datetime.datetime.now()) + " truncating CDRS segments in WICHWAY SPATIAL"
		
		TruncateTable_management(sdeWichwayCDRS)
		
		cdrsInsertCursor = daInsertCursor(sdeWichwayCDRS, insertCursorFields)
		
		for cdrsFeature in featuresToTransfer:
			insertOID = cdrsInsertCursor.insertRow(cdrsFeature)
			print "Inserted a row with the OID of: " + str(insertOID)
	
	except:
		print "An error occurred."
		errorItem = sys.exc_info()[1]
		print errorItem.args[0]
		try:
			del errorItem
		except:
			pass
	finally:
		try:
			del cdrsSearchCursor
		except:
			pass
		try:
			del cdrsInsertCursor
		except:
			pass


if __name__== "__main__":
	TnA()
	RemoveGpHistory_fc(metadataFolder)
	endtime = datetime.datetime.now()
	runtime = endtime-starttime
	print str(endtime) + " script completed in " + str(runtime)

else:
	print "CDRS_Update script imported."