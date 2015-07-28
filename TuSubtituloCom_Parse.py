# -*- coding: utf-8 -*-


import re
import urllib
from operator import itemgetter
import difflib

# from bs4 import BeautifulSoup

import os
import sys
cwd = os.path.dirname(os.path.realpath(__file__))
path = os.path.join(cwd, 'resources', 'libs', 'fuzzywuzzy')
sys.path.append (path)

#Got from: https://github.com/seatgeek/fuzzywuzzy developed by 
from fuzzywuzzy import fuzz

class TuSubtituloCom:
	def __init__(self,useSoundex = True):
		self.useSoundex = useSoundex
		self.log(__name__,"use soundex : %s" % (self.useSoundex))
		self.url = "http://www.tusubtitulo.com/"
		self.versionPattern = "<div id=\"version\" class=\"ssdiv\">(.+?)Versi&oacute;n(.+?)<span class=\"right traduccion\">(.+?)</div>(.+?)</div>"
		self.subtitlePattern = "<li class='li-idioma'>(.+?)<strong>(.+?)</strong>(.+?)<li class='li-estado (.+?)</li>(.+?)<span class='descargar green'>(.+?)<a href=\"(.+?)\">(.+?)</span>"
		self.tvShowPattern = "<a href=\"/show/([0-9]*)\">(.+?)</a>"
		self.tvShowDirectPattern = "<a href=\"/show/([0-9]*)\">%s</a>"

		self.languages = {
			# "Espanol": ("Spanish", "es", "ESP", 1),
			"Espanol (Espana)": ("Spanish", "es", "ESP", 1),
			"Espanol (Latinoamerica)": ("Latino", "es", "ESP", 2),
			"English": ("English", "en", "ENG", 2),
			"French": ("French", "fr", "FRE", 2),
			"Italian": ("Italian", "it", "ITA", 2),
			"Unknown": ("Unknown", "-", "???", 3),
		}

	def log(self,module, msg):
		#Delete all non utf8 characters
		msg = re.sub(r'[^\x00-\x7F]+',' ', msg)
		print (u"### [%s] - %s" % (module,msg,)).encode('utf-8')
		#xbmc.log((u"### [%s] - %s" % (module,msg,)).encode('utf-8'), level=xbmc.LOGDEBUG)

	"""
		Got this from: http://code.activestate.com/recipes/52213-soundex-algorithm/
	"""
	def soundex(self,name, len=4):
		""" soundex module conforming to Knuth's algorithm
			implementation 2000-12-24 by Gregory Jorgensen
			public domain
		"""

		# digits holds the soundex values for the alphabet
		digits = '01230120022455012623010202'
		# digits for spanish+english (comment by Scott David Daniels)
		#digits = '01230120002055012623010202';
		sndx = ''
		fc = ''

		# translate alpha chars in name to soundex digits
		for c in name.upper():
			if c.isalpha():
				if not fc: fc = c   # remember first letter
				d = digits[ord(c)-ord('A')]
				# duplicate consecutive soundex digits are skipped
				if not sndx or (d != sndx[-1]):
					sndx += d

		# replace first digit with first alpha character
		sndx = fc + sndx[1:]

		# remove all 0s from the soundex code
		sndx = sndx.replace('0','')

		# return soundex code padded to len characters
		return sndx
		return (sndx + (len * '0'))[:len]

	def getUrl(self,url):
		class AppURLopener(urllib.FancyURLopener):
			version = "App/1.7"
			def __init__(self, *args):
				urllib.FancyURLopener.__init__(self, *args)
			def add_referrer(self, url=None):
				if url:
					urllib._urlopener.addheader('Referer', url)

		urllib._urlopener = AppURLopener()
		urllib._urlopener.add_referrer("http://www.tusubtitulo.com/")
		try:
			response = urllib._urlopener.open(url)
			content    = response.read()
		except:
			content    = None
		return content

	def cleanSubtitleList(self,subtitlesList):
		seen = set()
		subs = []
		for sub in subtitlesList:
			filename = sub['link']
			if filename not in seen:
				subs.append(sub)
				seen.add(filename)
		return subs

	"""
	Get the show information from the site.
	Uses soundex algorithm to find shows with similar names
	Uses fuzzy matching lib ratio functionality, to sort matching shows
	"""
	def getTVShowInfoSoundex(self,content,tvShow):
		#Lowecase the show name
		tvShow = tvShow.lower()
		#Show first name
		tvShowFirstCharacter = tvShow[0]
		#Get show soundex value
		tvShowSoundex = self.soundex(tvShow,len(tvShow))
		self.log(__name__,"Searching show (%s,'%s',%s)" % (tvShow,tvShowFirstCharacter,tvShowSoundex))

		foundShows = list()
		#Search all the show names and links
		for matches in re.finditer(self.tvShowPattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
			#Get the show id, show name, and soundex value
			showId = matches.group(1)
			showName = matches.group(2)

			#Check for the firs characters to be the same as the searched show
			if showName[0] != tvShowFirstCharacter:
				continue

			showSoundex = self.soundex(showName,len(showName))

			#Check if shows name sound similar
			if tvShowSoundex == showSoundex:
				showRatio = fuzz.ratio(showName,tvShow)
				self.log(__name__,"%s,%s,%s,%s" % (showId,showName,showSoundex,showRatio))
				#Save the show in the list with the calculated ratio
				foundShows.append({"id":showId,"name":showName,"ratio":showRatio})

		if len(foundShows) != 0:
			#Sort by ratio and return first one (it is supposed to be the more accurate match)
			foundShows = sorted(foundShows, key=itemgetter('ratio'),reverse=True)
			return foundShows[0]
		else:
			return None


	"""
	Get the show information from the site.
	Uses several match methods to try get the show id
	"""
	def getTVShowInfoMatch(self,content,tvShow):
		#Lowecase the show name
		tvShow = tvShow.lower()
		self.log(__name__,"Searching show (%s)" % (tvShow))

		#Generate some name variations (got this from the old subtitulos.es xbmc plugin)
		tvShowVariations = list()
		tvShowVariations.append(tvShow)
		# Series name like "Shameless (US)" -> "Shameless US"
		if re.search(r'\([^)][a-zA-Z]*\)', tvShow):
			tvShowVariations.append(tvShow.replace('(', '').replace(')', ''))
		# Series name like "Scandal (2012)" -> "Scandal"
		if re.search(r'\([^)][0-9]*\)', tvShow):
			tvShowVariations.append(re.sub(r'\s\([^)]*\)', '', tvShow))
		# Series name like "Shameless (*)" -> "Shameless"
		if re.search(r'\([^)]*\)', tvShow):
			tvShowVariations.append(re.sub(r'\s\([^)]*\)', '', tvShow))
		# Clean dash,dots,underscore
		if re.search(r'-|_|\.', tvShow):
			tvShowVariations.append(re.sub(r'-|_|\.', ' ', tvShow).strip())

		print tvShowVariations

		for tvShowVariation in tvShowVariations:
			tvShowNameRegex = self.tvShowDirectPattern % tvShowVariation

			foundShow = None
			#Search all the show names that match the current show name pattern
			self.log(__name__,"Searching pattern (%s)" % tvShowNameRegex)
			for matches in re.finditer(tvShowNameRegex, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
				showId = matches.group(1)
				self.log(__name__,"Found %s,%s" % (showId,tvShowVariation))
				foundShow = {"id":showId,"name":tvShowVariation}
				break

			if foundShow is not None:
				break

		return foundShow


	def getTVShowSubtitles(self,tvShow, season, episode, languages):
		subtitlesList = list()

		#Get Series page to grab the show id
		content = self.getUrl(self.url+"series.php");
		if content is None:
			return None
		#Lowercase the content
		content = content.lower()

		#Try the regular search
		tvShowInfo = self.getTVShowInfoMatch(content,tvShow)
		#If there is no results and soundex is enabled search again
		if tvShowInfo is None and self.useSoundex:
			tvShowInfo = self.getTVShowInfoSoundex(content,tvShow)

		if tvShowInfo is None:
			return subtitlesList

		substitlesUrl = self.getSubtitlesUrl(tvShowInfo['id'],tvShowInfo['name'],season,episode)

		subtitlesList.extend(self.getSubtitlesFromUrl(substitlesUrl, languages, tvShowInfo['name'], season, episode))
		subtitlesList = self.cleanSubtitleList(subtitlesList)
		#Sort by order field
		subtitlesList = sorted(subtitlesList, key=itemgetter('order')) 

		return subtitlesList

	def getSubtitlesUrl(self,tvShowId,tvShow,season,episode):
		# Replace spaces with dashes
		tvShow = re.sub(r'\s', '-', tvShow)
		url = self.url + 'serie/' + tvShow + '/' + season + '/' + episode + '/' + tvShowId
		self.log(__name__,url)
		return url


	def getSubtitlesFromUrl(self,url, langs, tvShow, season, episode):
		subtitles_list = []

		content = self.getUrl(url)

		for matches in re.finditer(self.versionPattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
			
			filename = urllib.unquote_plus(matches.group(2))
			filename = re.sub(r' ', '.', filename)
			filename = re.sub(r'\s', '.', tvShow) + "." + season + "x" + episode + filename

			subs = matches.group(4)

			for matches in re.finditer(self.subtitlePattern, subs, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):

				lang = matches.group(2)
				lang = re.sub(r'\xc3\xb1', 'n', lang)
				lang = re.sub(r'\xc3\xa0', 'a', lang)
				lang = re.sub(r'\xc3\xa9', 'e', lang)

				if lang not in self.languages:
					lang = "Unknown"

				languageshort = self.languages[lang][1] 
				languagelong = self.languages[lang][0]
				order = 1 + self.languages[lang][3]
				server = filename

				#Get the id match and clean all the extra information
				id = matches.group(7)
				id = re.sub(r'([^-]*)href="', '', id)
				id = re.sub(r'" rel([^-]*)', '', id)
				id = re.sub(r'" re([^-]*)', '', id)
				id = re.sub(r'http://www.tusubtitulo.com/', '', id)

				if languageshort in langs:
					subtitles_list.append({'rating': "0", 'no_files': 1, 'filename': filename, 'server': server, 'sync': False, 'id' : id, 'language_flag': languageshort + '.gif', 'language_name': languagelong, 'hearing_imp': False, 'link': self.url + id, 'lang': languageshort, 'order': order, 'referer' : url})
				
		return subtitles_list
	
if __name__ == "__main__":
	#Use soundex to search the tv show
	search = TuSubtituloCom(True)
	subs = search.getTVShowSubtitles("Mr robot", "1", "5", "es")
	for sub in subs:
		print sub['server'], sub['link']
