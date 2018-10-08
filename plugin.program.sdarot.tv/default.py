# -*- coding: utf-8 -*-

import xbmcaddon,os,xbmc,xbmcgui,urllib,urllib2,xbmcplugin,sys,re
import logging,shutil
import time

AddonID='plugin.program.sdarot.tv'
Addon=xbmcaddon.Addon(id=AddonID)
addonIcon = Addon.getAddonInfo('icon')
addonFanart = Addon.getAddonInfo('fanart')
pluginpath = Addon.getAddonInfo('path')
sys.modules["__main__"].dbg = True
user_dataDir = xbmc.translatePath(Addon.getAddonInfo("profile")).decode("utf-8")

if not os.path.exists(user_dataDir): # check if folder doesnt exist 
     os.makedirs(user_dataDir) # create if it doesnt
download_list = user_dataDir + 'download_list.txt' # define watched as the path to txt file to store data 

addonsDir = xbmc.translatePath("special://home/addons/")

def get_params():
        param=[]
        if len(sys.argv)>=2:
          paramstring=sys.argv[2]
          if len(paramstring)>=2:
                params=sys.argv[2]
                cleanedparams=params.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
                                
        return param     
		
def addDir3(name,url,mode,iconimage,fanart,description):
	u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)+"&iconimage="+urllib.quote_plus(iconimage)+"&fanart="+urllib.quote_plus(fanart)+"&description="+urllib.quote_plus(description)
	ok=True
	liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
	liz.setInfo( type="Video", infoLabels={ "Title": name, "Plot": description } )
	liz.setProperty( "Fanart_Image", fanart )
	
	ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
	
	return ok

def addDir2(name,url,mode,iconimage,fanart,description):
    u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    liz.setInfo( type="Audio", infoLabels={ "Title": name } )
    if not fanart == '':
		liz.setProperty("Fanart_Image", fanart)
    ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
    return ok

def main_menu():    
      addDir3('התקנת הרחבה ותלויות','https://raw.githubusercontent.com/Sdarot/Repo-Sdarot/master/sdarot.txt',8,addonIcon,addonFanart,'')
      if os.path.exists(download_list):
       file = open(download_list, "r") 
       for f in file.readlines():
         
         name=''
         icon=''
         fanart=''
         read_text=read_txt_files(f)
         if read_text!='ERROR' :
           for line in read_text:
             if((line.split('=')[0])=='list name'):
               name=line.split('=')[1].rstrip('\r\n')
             if((line.split('=')[0])=='icon'):
               icon=line.split('=')[1].rstrip('\r\n')
             if((line.split('=')[0])=='fanart'):
               fanart=line.split('=')[1].rstrip('\r\n')
           if len(name)>0 and len(icon)>0 and len(fanart)>0:

             addDir3(name,f,8,icon,fanart,'')
    	  	
def setView(content, viewType):
    # set content type so library shows more views and info
    if content:
        xbmcplugin.setContent(int(sys.argv[1]), content)

def read_txt_files(target_url):
  try:
 
   target_url=target_url.rstrip('\r\n')
   if os.path.isfile(target_url):
    
    f=open(target_url, 'r') 
   else:
    f = urllib2.urlopen(target_url)
   return f.readlines()
  except:
    print 'ERROR: defname'
    return 'ERROR'

def swapUS(value):
	new = '"addons.unknownsources"'
	
	query = '{"jsonrpc":"2.0", "method":"Settings.GetSettingValue","params":{"setting":%s}, "id":1}' % (new)

	response = xbmc.executeJSONRPC(query)

	if 'false' in response:
		query = '{"jsonrpc":"2.0", "method":"Settings.SetSettingValue","params":{"setting":%s,"value":%s}, "id":1}' % (new, value)

		xbmc.executeJSONRPC(query)

		xbmc.executebuiltin('SendClick(11)')
		
	return False
		  
def add_addon_list(url):
     f =read_txt_files(url)
     if f!='ERROR':
      for file in f:
       if 'module.urllib3' in file and float(re.split(' |\-',xbmc.getInfoLabel('System.BuildVersion'))[0]) < 17:
         continue
       if 'unknownsources' in file and file[0]!="#":
         setting=file.split('=')[1]
         swapUS(setting.rstrip('\r\n'))
       if '$' in file and file[0]!="#":
        file_name=file.split("$")
        if file_name[0] == '':
         addDir2(file_name[1],file,99,addonIcon,addonFanart,'')
         continue
        if os.path.exists(os.path.join(addonsDir, file_name[2].replace('%24','$').rstrip('\r\n'))):
           file_name[1]='[COLOR white]'+file_name[1]+' - פעיל[/COLOR]'
        else:
          file_name[1]='[COLOR red]'+file_name[1]+' - לא פעיל[/COLOR]'
        addDir2(file_name[1],file,9,addonIcon,addonFanart,'')
  
def dis_or_enable_addon(addon_id, enable="true"):
    import json
    addon = '"%s"' % addon_id
    if xbmc.getCondVisibility("System.HasAddon(%s)" % addon_id) and enable == "true":
        logging.warning('already Enabled')
        return xbmc.log("### Skipped %s, reason = allready enabled" % addon_id)
    elif not xbmc.getCondVisibility("System.HasAddon(%s)" % addon_id) and enable == "false":
        return xbmc.log("### Skipped %s, reason = not installed" % addon_id)
    else:
        do_json = '{"jsonrpc":"2.0","id":1,"method":"Addons.SetAddonEnabled","params":{"addonid":%s,"enabled":%s}}' % (addon, enable)
        query = xbmc.executeJSONRPC(do_json)
        response = json.loads(query)
        if enable == "true":
            xbmc.log("### Enabled %s, response = %s" % (addon_id, response))
        else:
            xbmc.log("### Disabled %s, response = %s" % (addon_id, response))
    return xbmc.executebuiltin('Container.Update(%s)' % xbmc.getInfoLabel('Container.FolderPath'))
	
def ins_rem_package(url,with_massage):
    extension=url.split("$")
    addon_id = extension[2].rstrip('\r\n').replace('%24','$')
    if not os.path.exists(os.path.join(addonsDir, addon_id)):
      logging.warning(extension)
      downloader_is(extension[0],extension[1],with_massage)
      dis_or_enable_addon(addon_id)
      time.sleep(10)
      xbmc.executebuiltin("XBMC.UpdateLocalAddons()")
      if 'skin_change' in extension[1]:
       time.sleep(2)
       xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"lookandfeel.skin","value":"'+addon_id+'"}}')
       xbmc.executebuiltin('SendClick(11)')
       phenomenalSettings = os.path.join(xbmc.translatePath('special://home'),'userdata','addon_data','skin.phenomenal','settings.xml')
       if os.path.exists(phenomenalSettings):
            file=open(phenomenalSettings,'r')
            skin_setting=file.read()
            skin_setting=skin_setting.replace('<setting id="Disable_Splash" type="bool">false</setting>','<setting id="Disable_Splash" type="bool">true</setting>')
            file=open(phenomenalSettings,'w')
            file.write(skin_setting)
            file.close()
    elif with_massage=='yes':
      dialog = xbmcgui.Dialog()
      choice = dialog.yesno('[B][COLOR white]Sdarot.Tv Maintenance[/COLOR][/B]','', "האם להסיר את ההרחבה?",name.replace(' - פעיל',''))
      if choice :
        shutil.rmtree(os.path.join(addonsDir, addon_id))
        xbmc.executebuiltin("UpdateLocalAddons")
        xbmc.executebuiltin('Container.Refresh')
        dialog.ok("Sdarot.Tv", "ההסרה בוצעה בהצלחה!", "נא לבצע הפעלה מחדש לקודי.")

def downloader_is (url,name,with_massage ) :
 import downloader,extract   
 i1iIIII = xbmc . getInfoLabel ( "System.ProfileName" )
 I1 = xbmc . translatePath ( os . path . join ( 'special://home' , '' ) )
 O0OoOoo00o = xbmcgui . Dialog ( )
 if name.find('repo')< 0 and with_massage=='yes':
     choice = O0OoOoo00o . yesno ( '[B][COLOR white]Sdarot.Tv Maintenance[/COLOR][/B]' , "האם להתקין את ההרחבה?",'',name)
 else:
     choice=True
 if    choice :
  iiI1iIiI = xbmc . translatePath ( os . path . join ( 'special://home/addons' , 'packages' ) )
  iiiI11 = xbmcgui . DialogProgress ( )
  iiiI11 . create ( '[B][COLOR white]Sdarot.Tv Maintenance[/COLOR][/B]' , "מוריד " +name, '' , 'המתן בבקשה' )
  OOooO = os . path . join ( iiI1iIiI , 'isr.zip' )
  try :
     os . remove ( OOooO )
  except :
      pass
  downloader . download ( url , OOooO ,name, iiiI11 )
  II111iiii = xbmc . translatePath ( os . path . join ( 'special://home' , 'addons' ) )
  iiiI11 . update ( 0 , name , "מחלץ את הזיפ נא המתן" )

  extract . all ( OOooO , II111iiii , iiiI11 )
  iiiI11 . update ( 0 , name , "מוריד" )
  iiiI11 . update ( 0 , name , "מחלץ את הזיפ נא המתן" )
  xbmc.executebuiltin("UpdateLocalAddons")
  xbmc.executebuiltin('Container.Refresh')
  dialog = xbmcgui.Dialog()
  dialog.ok("Sdarot.Tv", "ההתקנה בוצעה בהצלחה!")
  
params=get_params()

url=None
name=None
mode=None
iconimage=None
fanart=None
description=None


try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        iconimage=urllib.unquote_plus(params["iconimage"])
except:
        pass
try:        
        mode=int(params["mode"])
except:
        pass
try:        
        fanart=urllib.unquote_plus(params["fanart"])
except:
        pass
try:        
        description=urllib.unquote_plus(params["description"])
except:
        pass
   
print "Mode: "+str(mode)
print "URL: "+str(url)
print "Name: "+str(name)

if mode==None or url==None or len(url)<1:
        main_menu()


elif mode==8:
        add_addon_list(url)
elif mode==9:
        ins_rem_package(url,'yes')



if len(sys.argv)>0:

 xbmcplugin.endOfDirectory(int(sys.argv[1]))
