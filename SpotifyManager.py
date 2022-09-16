#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#*################################################################################################*#
import os, sys, argparse,datetime, time, re
import pathlib
from pathlib import Path
import unicodedata

import spotipy
import spotipy.util as util
import mutagen
import configparser
from difflib import SequenceMatcher

from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.m4a import M4A
import mutagen.easymp4 as easyMp4

#*############################################################################*#
def enum(**enums):
    return type('Enum', (), enums)
#*############################################################################*#
eCfgLogLevel = enum(MAIN=0, INFO=1, DBGLEVEL1=2, DBGLEVEL2=3, DBGLEVEL3=4)
eUser = enum(NICO=0, JEANNE=1)
ePosXExitCode = enum(OK=0, ERROR=1, MISUSE=2, CANNOTEXE=126, NOTFOUND=127, INVALID=128, CTRLC=130, OUTOFRANGE=255)
eSpotifyManagerAction = enum(NONE=0, IMPORTPLAYLIST=1, SEARCH=2)
g_scope = 'user-library-read playlist-modify-private'
g_redirect_uri = 'http://localhost:8888/callback'
g_defaultArg = 'default'
g_liOfUsers = [ {'userLabel':'nico',   'userId':eUser.NICO},
                {'userLabel':'jeanne', 'userId':eUser.JEANNE}]

g_selectedUser = g_liOfUsers[eUser.NICO]

# Nico's credentials
g_user_name_nico = 'wy6wpr1uhh89pnkxg0jzspm64'
g_client_id_nico = 'ac03525431bb45fda021c313a8c2d3c6'
g_client_secret_nico = 'd181274d90dc4c42a969787ba6499df4'
# Jeanne's credentials
g_user_name_jeanne = 'jcfqtwfm00ipqbhkjw6ksfeu7'
g_client_id_jeanne = 'a26231ca94e04dbf8f8a8d3c797bd697'
g_client_secret_jeanne = '8d1813097b2648dd884915fc51e89708'


g_diOfTrackMembers = ['track', 'artist', 'album', 'title']
#*############################################################################*#
def getUserId(userString):
    for u in g_liOfUsers:
        if userString in u['userLabel']:
            return u

    print('unknow user exit ...')
    exit(ePosXExitCode.ERROR)
#*############################################################################*#
def execCmd(cmd):   
    process = Popen(cmd, shell=True, stderr=PIPE, stdout=PIPE)
    globLogs = ''
    (output, err) = process.communicate()
    p_status = process.wait()
    globLogs += output
    return globLogs, err, process.returncode

#*############################################################################*#
def myFindFiles(myPath, myPattern):    
    liOfFiles = []
    for root, dirs, files in os.walk(myPath):
        for basename in files:
            if fnmatch.fnmatch(basename, myPattern):
                filename = os.path.join(root, basename)
                liOfFiles.append(filename)
    return liOfFiles

#*############################################################################*#
class InOut():
    def __init__(self,ioLogFilename, logInFile):
        
        self.logInFile = logInFile
        self.ioLogFilename = ioLogFilename
        self.dbgLevel = eCfgLogLevel.INFO
        self.dumpInitLogs()

    def addDbgLogs(self,dbgLogs):
        locCurDate = datetime.datetime.now()
        y = locCurDate.strftime("%y")
        timeFormated = '[%02d-%02d-%02d][%02d:%02d:%02d]' % (locCurDate.year, locCurDate.month,  locCurDate.day, 
                                                             locCurDate.hour, locCurDate.minute, locCurDate.second)        
        logging.debug('%s %s', (timeFormated, dbgLogs))

    def addDbgInfo(self, dbgLevel, infoLog):
        locCurDate = datetime.datetime.now()
        y = locCurDate.strftime("%y")
        timeFormated = '[%02d-%02d-%02d][%02d:%02d:%02d]' % (locCurDate.year, locCurDate.month,  locCurDate.day, 
                                                             locCurDate.hour, locCurDate.minute, locCurDate.second)
        if dbgLevel <= self.dbgLevel:        
            logging.info('%s %s', (timeFormated, infoLog))

    def printInfo(self,dbgLevel,infoLog):
        if dbgLevel <= self.dbgLevel:
            locCurDate = datetime.datetime.now()
            y = locCurDate.strftime("%y")
            nbLine = infoLog.count('\n')
            lineJump = ''            
            for l in range(0, nbLine): lineJump += '\n'             
            timeFormated = '[%02d-%02d-%02d][%02d:%02d:%02d]' % (locCurDate.year, locCurDate.month,  locCurDate.day, 
                                                                 locCurDate.hour, locCurDate.minute, locCurDate.second)
            print('%s %s %s' % (lineJump, timeFormated, infoLog.replace('\n','')))
            if self.logInFile:                
                self.addDbgLogs(infoLog)

    def addDbgWarning(self,warningLog):
        logging.warning('%s', warningLog)

    def setDbgLevel(self,dbgLevel,logInFile):
        self.dbgLevel = dbgLevel
        self.logInFile = logInFile
        self.dumpInitLogs()

    def dumpInitLogs(self):        
        if self.logInFile:
            logging.basicConfig(format='%(asctime)s | %(message)s',filename=self.ioLogFilename,filemode='w',level=logging.DEBUG)
            self.addDbgLogs('Starting processCsv')
            self.addDbgLogs('LogFile: %s' % self.ioLogFilename)
#*############################################################################*#
class TimeStats:
    def __init__(self):
        self.startTime = {}
        self.stopTime =  {}
        self.processTime = {}                

    def setStartTime(self,cfg):
        self.startTime[cfg] = time.time()

    def setEndTime(self,cfg):
        self.stopTime[cfg] = time.time()
        self.processTime[cfg] = float(self.stopTime[cfg] - self.startTime[cfg])        

    def getProcessTime(self,cfg):
        return self.processTime[cfg]
    
    def getDiOfProcessTime(self):
        return self.processTime
# *############################################################################*#
class cTrack(object):
    def __init__(self, d):
        self.__dict__ = d

    def setSpotifyData(self, spotifyData):
        self.__dict__['spotify_data'] = spotifyData

    def get(self,key):
        return self.__dict__[key]

    def isValid(self):
        return 'artist' in self.__dict__

# *############################################################################*#
class cSearchPattern:
    def __init__(self, searchString, title):
        self.searchString = searchString
        self.title = title



#*############################################################################*#
class cSpotifyManagerCfg:

    def __init__(self):
        
        self.dbgLevel = eCfgLogLevel.INFO
        self.logInFile = False        
        self.configFilename = ''
        self.myTimeStats = TimeStats()
        self.myTimeStats.setStartTime("global")                       
        self.cfgFileParser = configparser.ConfigParser()

    def epilogue(self):
        self.myTimeStats.setEndTime('global')
        diOfProcessTime = self.myTimeStats.getDiOfProcessTime()
        
        timeStatLableLen = 20
        for k, v in diOfProcessTime.items():
            if not 'global' in k:
                timeStatLabel = '%-*s' %(timeStatLableLen, k)
                self.io.printInfo(eCfgLogLevel.MAIN , ('%s \t %0.2fsec\n' % (timeStatLabel, v)))

        timeStatLabel = '%-*s' %(timeStatLableLen, 'global')                
        self.io.printInfo(eCfgLogLevel.MAIN , ('%s \t %0.2fsec\n' % (timeStatLabel, diOfProcessTime['global'])))

    def setIoModule(self,io):
        self.io = io
        self.io.setDbgLevel(self.dbgLevel,self.logInFile)
    
    def parseArgs(self):
        args = sys.argv[1:]        
        ArgParser = argparse.ArgumentParser(description='Allows to manage your Spotify operation')
        # Mandatory args        
        requiredNamed = ArgParser.add_argument_group('required arguments')
        requiredNamed.add_argument('-u', '--user',                  default='nico', type=str,                    help='spotify user see username in profil overall page')
        requiredNamed.add_argument('-i', '--import_playlist', default=g_defaultArg, type=argparse.FileType('r'), help='Path to m3u playlist file')
    
        # Optionnal args
        requiredNamed = ArgParser.add_argument_group('optional arguments')
        ArgParser.add_argument('--log',             default='0',     type=int,            help='log level 0 to 4')

        self.argParser = ArgParser
        self.cfgArgs = ArgParser.parse_args()

    def printUsage(self):
        self.argParser.print_help()
        
    def checkConfig(self):
        status = False
        self.dbgLevel = self.cfgArgs.log
        self.playListFile = self.cfgArgs.import_playlist
        self.playlistName = g_defaultArg
        self.user = getUserId(self.cfgArgs.user.lower())

        if self.user['userId'] == eUser.NICO:
            self.userName = g_user_name_nico
            self.clientId = g_client_id_nico
            self.clientSecret = g_client_secret_nico
        elif self.user['userId'] == eUser.JEANNE:
            self.userName = g_user_name_jeanne
            self.clientId = g_client_id_jeanne
            self.clientSecret = g_client_secret_jeanne

        self.importPlaylist = False

        if self.playListFile != g_defaultArg:
            p =Path(self.playListFile.name)
            self.playlistName = p.stem
            self.importPlaylist = True
            status = True

            token = util.prompt_for_user_token(self.userName,
                                               scope=g_scope,
                                               client_id=self.clientId, client_secret=self.clientSecret,
                                               redirect_uri=g_redirect_uri,show_dialog = True)
            if token:
                self.mySpotify = spotipy.Spotify(auth=token)
            else:
                self.io.printInfo(eCfgLogLevel.MAIN ,'Can\'t get token for user %s' % self.user['userLabel'])
                return


        return status


#*############################################################################*#
class cSpotifyManager:

    def __init__(self):
        self.liOfTracks = []

    def prologue(self, cfg, io):
        self.cfg = cfg        
        self.cfg.parseArgs()
        if self.cfg.checkConfig():
            self.cfg.setIoModule(io)
        else:
            self.cfg.printUsage()
            exit()

    def epilogue(self):
        self.cfg.epilogue()

    def loadPlaylistFromFile(self, playlistFile):
        self.cfg.io.printInfo(eCfgLogLevel.MAIN, 'Loading playlist from %s' % playlistFile.name)
        tracks = []
        try:
            content = [line.strip() for line in playlistFile if line.strip() and not line.startswith("#")]
        except Exception as e:
            self.cfg.io.printInfo(eCfgLogLevel.MAIN,'Playlist file "%s" failed load: %s' % (playlistFile.name, str(e)))
            sys.exit(1)
        else:
            liOfAddedTracks = []
            for track in content:
                if track not in liOfAddedTracks:
                    liOfAddedTracks.append(track)
                    tracks.append({'path': track})
            return tracks

    def getMp3TagsFromFile(self, mp3File):

        try:
            info = mutagen.File(mp3File)
            if isinstance(info, mutagen.mp3.MP3):
                # We really want an EasyID3 object, so we re-read the tags now.
                # Alas, EasyID3 does not include the .info part, which contains
                # the length, so we save it from the MP3 object.
                dot_info = info.info
                try:
                    info = mutagen.easyid3.EasyID3(mp3File)
                except mutagen.id3.ID3NoHeaderError:
                    info = mutagen.easyid3.EasyID3()
                info.info = dot_info
            elif info is None:
                self.cfg.io.printInfo(eCfgLogLevel.MAIN,
                                      'Could not read tags from %s: mutagen.File() returned None' % mp3File)
                return {}
        except Exception as e:
            if mp3File in str(e):  # Mutagen included the path in the exception.
                msg = 'could not read tags: %s' % e
            else:
                msg = 'could not read tags from %s: %s' % (mp3File, e)
            self.cfg.io.printInfo(eCfgLogLevel.MAIN, msg)
            return {}

        tags = {}

        for column in g_diOfTrackMembers:
            if column == 'track':
                tag = 'tracknumber'
            else:
                tag = column.lower()
            try:
                tags[column] = info[tag][0]
            except ValueError:
                self.cfg.io.printInfo(eCfgLogLevel.MAIN, 'invalid tag %r for %s' % (tag, type(info)))
            except KeyError:
                pass  # Tag is not present in the file.
        try:
            tags['Length'] = int(info.info.length)
        except AttributeError:
            pass

        return tags

    def getFlacTagsFromFile(self, flacFile):

        try:
            info = mutagen.File(flacFile)
            if isinstance(info, mutagen.flac.FLAC):
                info = FLAC(flacFile)
            elif info is None:
                self.cfg.io.printInfo(eCfgLogLevel.MAIN, 'Could not read tags from %s: mutagen.File() returned None' % flacFile)
                return {}
        except Exception as e:
            if flacFile in str(e):  # Mutagen included the path in the exception.
                msg = 'could not read tags: %s' % e
            else:
                msg = 'could not read tags from %s: %s' % (flacFile, e)
            self.cfg.io.printInfo(eCfgLogLevel.MAIN, msg)
            return {}

        tags = {}

        for column in g_diOfTrackMembers:
            if column == 'track':
                tag = 'tracknumber'
            else:
                tag = column.lower()
            try:
                tags[column] = info[tag][0]
            except ValueError:
                self.cfg.io.printInfo(eCfgLogLevel.MAIN, 'invalid tag %r for %s', tag, type(info))
            except KeyError:
                pass  # Tag is not present in the file.
        try:
            tags['Length'] = int(info.info.length)
        except AttributeError:
            pass

        return tags


    def getM4aTagsFromFile(self, m4aFile):

        try:
            info = easyMp4.EasyMP4(m4aFile)
        except Exception as e:
            if m4aFile in str(e):  # Mutagen included the path in the exception.
                msg = 'could not read tags: %s' % e
            else:
                msg = 'could not read tags from %s: %s' % (m4aFile, e)
            self.cfg.io.printInfo(eCfgLogLevel.MAIN, msg)
            return {}

        tags = {}

        for column in g_diOfTrackMembers:
            if column == 'track':
                tag = 'tracknumber'
            else:
                tag = column.lower()
            try:
                tags[column] = info[tag][0]
            except ValueError:
                self.cfg.io.printInfo(eCfgLogLevel.MAIN, 'invalid tag %r for %s', tag, type(info))
            except KeyError:
                pass  # Tag is not present in the file.
        try:
            tags['Length'] = int(info.info.length)
        except AttributeError:
            pass

        return tags

    def getListOfPatterns(self, track):
        liOfPatterns = []
        liOfPatterns.append(cSearchPattern('%s %s' % (track.artist, track.album), track.title))
        liOfPatterns.append(cSearchPattern('%s %s' % (track.artist, track.title), track.title))
        liOfPatterns.append(cSearchPattern('%s %s' % (track.album, track.title), track.title))

        if 'various' in track.artist:
            liOfPatterns.append(cSearchPattern('%s' % track.title , track.title))

        if '&' in track.artist:
            liOfPatterns.append(cSearchPattern('%s %s' % (track.artist.split('&')[0], track.title), track.title))
        if '(' in track.artist:
            liOfPatterns.append(cSearchPattern('%s %s' % (track.artist.split('(')[0], track.title), track.title))
        if 'feat' in track.artist:
            liOfPatterns.append(cSearchPattern('%s %s' % (track.artist.split('feat')[0], track.title), track.title))

        if '&' in track.title:
            t = track.title.split('&')[0]
            liOfPatterns.append(cSearchPattern('%s %s' % (track.artist, t), t))
        if '(' in track.title:
            t = track.title.split('(')[0]
            liOfPatterns.append(cSearchPattern('%s %s' % (track.artist, t), t))
        if 'feat' in track.title:
            t = track.title.split('feat')[0]
            liOfPatterns.append(cSearchPattern('%s %s' % (track.artist, t), t))

        if '.' in track.title:
            t = track.title.replace('.', ' ')
            liOfPatterns.append(cSearchPattern('%s %s' % (track.artist, t), t))
        if '.' in track.title:
            t = track.title.split('.')[0]
            liOfPatterns.append(cSearchPattern('%s %s' % (track.artist, t), t))

        return liOfPatterns
    def howSimilar(self, a, b, searchString, spotifyMatchThreshold, trackName):
        ratio = SequenceMatcher(None, a, b, spotifyMatchThreshold).ratio()
        if ratio < spotifyMatchThreshold:
            if searchString in trackName or trackName in searchString:
                ratio = spotifyMatchThreshold + 0.1
        return ratio
    def selectResultFromSpotifySearch(self, searchString, trackName, trackAlbum, trackArtist):
        self.cfg.io.printInfo(eCfgLogLevel.DBGLEVEL1,
                              'Searching Spotify for "%s" trying to find track called "%s"' % (searchString, trackName))
        spotifyMatchThreshold = 0.5

        # if trackAlbum != None:
        #   resultsRaw = self.cfg.mySpotify.search(q=trackAlbum.lower(), type='album', limit=30)
        #    if resultsRaw:
        #        albumId = resultsRaw['albums']['items'][0]['id']
        #        resultsRaw = self.cfg.mySpotify.album_tracks(albumId, limit=30)
        # else:

        try:
            resultsRaw = self.cfg.mySpotify.search(q=searchString, type='track', limit=50)
        except:
            self.cfg.io.printInfo(eCfgLogLevel.INFO, 'Not found: %s ' % searchString)
            return 0

        if len(resultsRaw['tracks']['items']) > 0:
            spotifyResults = resultsRaw['tracks']['items']
            self.cfg.io.printInfo(eCfgLogLevel.DBGLEVEL1, 'Spotify results:%s' % len(spotifyResults))

            cleanTrackAlbum = re.sub('\W+', '', trackAlbum).lower()
            cleanTrackArtist = re.sub('\W+', '', trackArtist).lower()

            for spotifyResult in spotifyResults:
                cleanSpotAlbum = re.sub('\W+', '', spotifyResult['album']['name']).lower()

                cleanSpotArtist = ""
                if len(spotifyResult['artists']) > 0:
                    cleanSpotArtist = re.sub('\W+', '', spotifyResult['artists'][0]['name']).lower()

                albumTargeted = cleanTrackAlbum in cleanSpotAlbum or cleanSpotAlbum in cleanTrackAlbum
                artistTargeted = (cleanTrackArtist in cleanSpotArtist) or (cleanSpotArtist in cleanTrackArtist)

                if (albumTargeted and artistTargeted):
                    cleanTrackName = re.sub('\W+', '', trackName).lower()
                    cleanSpotTrackName = re.sub('\W+', '', spotifyResult['name']).lower()
                    spotifyResult['rank'] = self.howSimilar(cleanTrackName, cleanSpotTrackName, searchString,
                                                            spotifyMatchThreshold, trackName)
                    if spotifyResult['rank'] == 1.0:
                        return {'id': spotifyResult['id'], 'title': spotifyResult['name'],
                                'artist': spotifyResult['artists'][0]['name']}
                else:
                    spotifyResult['rank'] = 0.0

            # Sorting results using their rank
            spotifyResultsSorted = sorted(spotifyResults, key=lambda k: k['rank'], reverse=True)
            if len(spotifyResultsSorted) > 0 and spotifyResultsSorted[0]['rank'] > spotifyMatchThreshold:
                return {'id': spotifyResultsSorted[0]['id'], 'title': spotifyResultsSorted[0]['name'],
                        'artist': spotifyResultsSorted[0]['artists'][0]['name']}
        self.cfg.io.printInfo(eCfgLogLevel.DBGLEVEL1, 'No good Spotify result found')
        return 0

    def findTracksInSpotifyDatabase(self, track):

        seachResult = False
        listOfPattern = self.getListOfPatterns(track)
        for p in listOfPattern:
            seachResult = self.selectResultFromSpotifySearch(p.searchString, p.title, track.album, track.artist)
            if seachResult:
                return seachResult
        return False

    def getTrackTags(self, path):
        tags = {}
        if os.path.exists(path):
            extension = os.path.splitext(path)[1][1:].strip()
            if extension.lower() == 'mp3':
                tags = self.getMp3TagsFromFile(path)
            elif extension.lower() == 'flac':
                tags = self.getFlacTagsFromFile(path)
            elif extension.lower() == 'm4a':
                tags = self.getM4aTagsFromFile(path)
            else:
                self.cfg.io.printInfo(eCfgLogLevel.MAIN, '%s files not managed' % extension)

            for m in g_diOfTrackMembers:
                if m in tags:
                    tags[m] = unicodedata.normalize('NFKD', tags[m]).encode('ascii', 'ignore').decode('utf8').lower()
                else:
                    tags[m] = 'undef'
        else:
            self.cfg.io.printInfo(eCfgLogLevel.MAIN, '%s is not a valid path' % path)
        return tags

    def createPlaylist(self, playListName, tracks):
        self.cfg.io.printInfo(eCfgLogLevel.MAIN, 'Creating playlist %s' % self.cfg.playlistName)
        liOfSpotifyTracks = []
        nbFounded = 0
        NbTracks = len(tracks)
        for track in tracks:
            t = track['path']
            tPath = os.path.join(t)
            loadedTags = self.getTrackTags(tPath)
            t = cTrack(loadedTags)
            if t.isValid():
                spotifyTrackData = self.findTracksInSpotifyDatabase(t)
                if spotifyTrackData:
                    t.setSpotifyData(spotifyTrackData)
                    self.liOfTracks.append(t)
                    track['spotify_data'] = spotifyTrackData
                    nbFounded += 1
                    self.cfg.io.printInfo(eCfgLogLevel.DBGLEVEL1, 'Loaded %s - %s - %s' % (t.track, t.artist, t.title))
                else:
                    self.cfg.io.printInfo(eCfgLogLevel.INFO, '%s - %s - %s not found on spotify' % (t.track, t.artist, t.title))
            else:
                self.cfg.io.printInfo(eCfgLogLevel.MAIN, '%s can not be read' % (track['path']))

        # Remove duplicated tracks
        liOfSpotifyTracks = [k['spotify_data']['id'] for k in tracks if k.get('spotify_data')]

        self.cfg.io.printInfo(eCfgLogLevel.MAIN, 'Nb Track loaded %d - NbFound on Spotify %d => %0.2f %%' % (NbTracks, nbFounded, float(100 * nbFounded) / float(NbTracks)))

 #       try:
        self.cfg.mySpotify.trace = False
        playlist = self.cfg.mySpotify.user_playlist_create(self.cfg.userName, self.cfg.playlistName, public=False)

        if len(liOfSpotifyTracks) > 100:
            def chunker(seq, size):
                return (seq[pos:pos + size] for pos in range(0, len(seq), size))
            for spotify_tracks_chunk in chunker(liOfSpotifyTracks, 100):
                results = self.cfg.mySpotify.user_playlist_add_tracks(self.cfg.userName, playlist['id'], spotify_tracks_chunk)
        else:
            results = self.cfg.mySpotify.user_playlist_add_tracks(self.cfg.userName, playlist['id'], liOfSpotifyTracks)

#        except Exception as e:
#            self.cfg.io.printInfo(eCfgLogLevel.MAIN, 'Spotify error: %s' % str(e))

    def performAction(self):

        if self.cfg.importPlaylist:
            tracks = self.loadPlaylistFromFile(self.cfg.playListFile)
            self.createPlaylist(self.cfg.playlistName, tracks)

# *############################################################################*#

# *###########################################################################*#
# Main
# *###########################################################################*#
def main():
    # Token refresh
    #https://accounts.spotify.com/authorize?response_type=code&client_id=a26231ca94e04dbf8f8a8d3c797bd697&scope=user-library-read playlist-modify-private&redirect_uri=http://localhost:8888/callback


    io = InOut('debug.log', False)
    cfg = cSpotifyManagerCfg()
    spotifyManager = cSpotifyManager()
    spotifyManager.prologue(cfg, io)
    spotifyManager.performAction()
    spotifyManager.epilogue()
    
# *###########################################################################*#
main()
