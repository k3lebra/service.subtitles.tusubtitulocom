# -*- coding: utf-8 -*- 
"""
XBMC Code from the subtitulos.es plugin adapted to use the new scrapper for www.tusubtitulo.com
Done by therudo

Old subtitulos.es thanks:
This addon is a modification of quillo86's addon for XBMC Frodo, adapted to Gotham using
manacker's service.subtitles.subscene as base code

Original code by quillo86 (https://github.com/quillo86) and manacker (https://github.com/manacker)
Adaptation by infinito (https://github.com/infinicode)
"""

import os
import sys
import xbmc
import urllib
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import re
import shutil
import unicodedata
import urllib2

__addon__ = xbmcaddon.Addon()
__author__     = __addon__.getAddonInfo('author')
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString
__cwd__        = xbmc.translatePath( __addon__.getAddonInfo('path') ).decode("utf-8")
__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
__temp__       = xbmc.translatePath( os.path.join( __profile__, 'temp') ).decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'libs', 'fuzzywuzzy' ) ).decode("utf-8")
__handle__ = int(sys.argv[1])
sys.path.append (__resource__)

#Import the class after the lib path has been appended (fuzzywuzzy lib)
from TuSubtituloCom import TuSubtituloCom

class TuSubtituloComService:
	def __init__(self,scriptId,handleId):
		self.handleId = handleId
		self.scriptId = scriptId
		self.scraper = TuSubtituloCom()

	def log(self,module, msg):
		#Delete all non utf8 characters
		msg = re.sub(r'[^\x00-\x7F]+',' ', msg)
		print (u"### [%s] - %s" % (module,msg,)).encode('utf-8')
		# xbmc.log((u"### [%s] - %s" % (module,msg,)).encode('utf-8'), level=xbmc.LOGDEBUG)


	def addSubtitle(self,subtitle):
		listItem = xbmcgui.ListItem(label=subtitle.getLanguage(),  label2=subtitle.getFilename(), iconImage=subtitle.getRating(), thumbnailImage=subtitle.getLanguageCode())
		listItem.setProperty("sync",  'true' if substitle.isSyched() else 'false')
		listItem.setProperty("hearing_imp", 'true' if substitle.isHearing() else 'false')
		url = "plugin://%s/?action=download&link=%s&filename=%s&referer=%s" % (self.scriptid, subtitle.getLink(), subtitle.getFilename(), subtitle.getReferer())
		xbmcplugin.addDirectoryItem(handle=self.handleId, url=url, listitem=listItem, isFolder=False)

	def getSubtitles(self,tvShow,season,episode,language):
		subtitles = self.scraper.getTVShowSubtitles(tvShow,season,episode,language)
		for subtitle in subtitles:
			self.addSubtitle(subtitle)

	def download(self,link,filename,referer):
		subtitle_list = []

		if link:
				downloadlink = link
				self.log(__name__, "Downloadlink %s" % link)

				class MyOpener(urllib.FancyURLopener):
						version = "User-Agent=Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)"

				my_urlopener = MyOpener()
				my_urlopener.addheader('Referer', referer)
				postparams = None
				
				
				self.log(__name__, "Fetching subtitles using url '%s' with referer header '%s' and post parameters '%s'" % (link, link, postparams))
				response = my_urlopener.open(link, postparams)
				local_tmp_file = os.path.join(__temp__, "sub.srt")
				
				if xbmcvfs.exists(__temp__):
						shutil.rmtree(__temp__)
				xbmcvfs.mkdirs(__temp__)
				try:
						self.log(__name__, "Saving subtitles to '%s'" % local_tmp_file)
						local_file_handle = open(local_tmp_file, "wb")
						local_file_handle.write(response.read())
						local_file_handle.close()
						
						subtitle_list.append(local_tmp_file)
						self.log(__name__, "=== returning subtitle file %s" % file)

				except:
						self.log(__name__, "Failed to save subtitle to %s" % local_tmp_file)

		return subtitle_list
	def normalizeString(self,str):
		return unicodedata.normalize(
				 'NFKD', unicode(unicode(str, 'utf-8'))
				 ).encode('ascii','ignore')    
	def getParameters(self):
		param=[]
		paramstring=sys.argv[2]
		if len(paramstring)>=2:
			params=paramstring
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

	def proxy(self):
		params = self.getParameters()
		if params['action'] == 'search':
			item = {}
			item['temp']               = False
			item['rar']                = False
			item['year']               = xbmc.getInfoLabel("VideoPlayer.Year")                           # Year
			item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))                    # Season
			item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                   # Episode
			item['tvshow']             = self.normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))   # Show
			item['title']              = self.normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle")) # try to get original title
			item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))  # Full path of a playing file
			item['3let_language']      = []
			item['2let_language']      = []
			
			for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
				item['3let_language'].append(xbmc.convertLanguage(lang,xbmc.ISO_639_2))
				item['2let_language'].append(xbmc.convertLanguage(lang,xbmc.ISO_639_1))
			
			if item['title'] == "":
				item['title']  = self.normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))      # no original title, get just Title
			
			if item['episode'].lower().find("s") > -1:                                      # Check if season is "Special"
				item['season'] = "0"                                                          #
				item['episode'] = item['episode'][-1:]
			
			if ( item['file_original_path'].find("http") > -1 ):
				item['temp'] = True

			elif ( item['file_original_path'].find("rar://") > -1 ):
				item['rar']  = True
				item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

			elif ( item['file_original_path'].find("stack://") > -1 ):
				stackPath = item['file_original_path'].split(" , ")
				item['file_original_path'] = stackPath[0][8:]

			# required if tvshow is not indexed/recognized in library
			if item['tvshow'] == "":  
				self.log(__name__, "item %s" % item)
				# replace dots with spaces in title
				titulo = re.sub(r'\.', ' ', item['title'])
				self.log(__name__, "title no dots: %s" % titulo)
				mo = re.search(r'(.*)[sS](\d+)[eE](\d+)', titulo) #S01E02 like
				if not mo:
					mo = re.search(r'(.*)(\d\d)[xX](\d+)', titulo) # old 10x02 style
				if not mo:
					mo = re.search(r'(.*)(\d)[xX](\d+)', titulo) # old 1x02 style
				if not mo:
					mo = re.search(r'(.*) (\d+)(\d\d)', titulo) # 102 style 

				# split title in tvshow, season and episode
				if mo:
					item['tvshow'] = mo.group(1)
					item['season'] = mo.group(2)
					item['episode'] = mo.group(3)
					self.log(__name__, "item %s" % item)
	
			if item['tvshow'] != "":
				self.getSubtitles(item["tvshow"],item["season"],item["episode"],item["2let_language"])

			print item
		elif params['action'] == 'download':
			subs = self.download(params["link"],params["filename"],params["referer"])
			for sub in subs:
				listitem = xbmcgui.ListItem(label=sub)
				xbmcplugin.addDirectoryItem(handle=self.handleId,url=sub,listitem=listitem,isFolder=False)
	

service = TuSubtituloComService(__scriptid__,__handle__)
service.proxy()

xbmcplugin.endOfDirectory(__handle__)
	
	
	
	
	
	
	
	
	
		
