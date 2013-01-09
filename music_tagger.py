#!/usr/bin/python

#-----------------------------------------------------------------------#
#----------------------------    LICENSE    ----------------------------#
#-----------------------------------------------------------------------#
# This file is part of the music_tagger program                         #
# (https://github.com/jonsim/music_tagger).                             #
#                                                                       #
# Foobar is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU General Public License as published by  #
# the Free Software Foundation, either version 3 of the License, or     #
# (at your option) any later version.                                   #
#                                                                       #
# Foobar is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of        #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
# GNU General Public License for more details.                          #
#                                                                       #
# You should have received a copy of the GNU General Public License     #
# along with Foobar.  If not, see <http://www.gnu.org/licenses/>.       #
#-----------------------------------------------------------------------#


#-----------------------------------------------------------------------#
#----------------------------     ABOUT     ----------------------------#
#-----------------------------------------------------------------------#
# A small program to tidy music files. It recursively explores a given  #
# directory and standardises folder structures, file naming conventions #
# and ID3 tags.                                                         #
# Author: Jonathan Simmonds                                             #
#-----------------------------------------------------------------------#


#-----------------------------------------------------------------------#
#----------------------------    IMPORTS    ----------------------------#
#-----------------------------------------------------------------------#
import sys, string, os, re



#-----------------------------------------------------------------------#
#------------------------    CLASS DEFINITIONS    ----------------------#
#-----------------------------------------------------------------------#
#class Artist:
#    artist_name = ""
#    albums = []

#class Album:
#    album_name = ""
#    album_date = ""
#    songs = []

#class Song:
#    track_name   = ""
#    track_number = 0

class MusicFile:
    file_path    = ""
    artist_name  = ""
    album_name   = ""
    album_year   = 0
    track_name   = ""
    track_number = 0
    
    
    # Loads the object with all the song data. The file path provides the majority of the information
    # though a cleaned_filename needs to be passed in (which is designed to be one of the outputs
    # from clean_folder()) as this method will have access to only the single file, not the entire
    # folder of files which is necessary for the full cleaning (e.g. removing repeated words).
    def __init__ (self, file_path, cleaned_filename):
        # Save the file path
        self.file_path = file_path
        
        # Attemtpt to collect information from the file's path (the album / artist).
        file_path_split = file_path.split("/")
        # If correctly set up: -1 holds the file name; -2 the album folder; -3 the artist folder.
        if len(file_path_split) >= 3:
            candidate_album_name = clean_string(file_path_split[-2])
            if re.match('\[\d\d\d\d\] ', candidate_album_name) != None:
                self.album_name = candidate_album_name[7:]
                self.album_year = int(candidate_album_name[1:5])
            else:
                self.album_name = candidate_album_name
            self.album_artist = clean_string(file_path_split[-3])
        
        # Attempt to collect information from the file's name (the track number / name).
        #filename_split = clean_string(file_path_split[-1]).split()
        filename_split = cleaned_filename.split()
        if filename_split[0].isdigit():
            self.track_number = int(filename_split[0])
            self.track_name = ' '.join(filename_split[1:]).split('.')[0]
        else:
            self.track_name = ' '.join(filename_split).split('.')[0]
    
    
    def __str__ (self):
        if self.album_year > 0:
            return "#%02d '%s' - '%s' by '%s' in %d." % (self.track_number, self.track_name, self.album_name, self.artist_name, self.album_year)
        else:
            return "#%02d '%s' - '%s' by '%s'."       % (self.track_number, self.track_name, self.album_name, self.artist_name)
    
    
    def write_to_ID3_tag ():
        return




#-----------------------------------------------------------------------#
#----------------------    FUNCTION DEFINITIONS    ---------------------#
#-----------------------------------------------------------------------#
# Strips extraneous whitespace and null bytes from some given data, leaving a string.
def strip_null_bytes (data):
    return data.replace("\00", "").strip()


# Packs a given string into a given number of bytes and null terminates it. This is
# achieved either by truncating (when too long) or adding null bytes (when too short).
def pack_null_bytes (string, length):
    if len(string) >= length-1:
        data = string[:length-1] + '\00'
    else:
        data = string + ('\00' * (length - len(string)))
    return data


# Reads the ID3v1 tag data from a file (if present). ID3 v1.0 and v1.1 tags are supported along with extended tags.
def read_id3_v1_tag (file_path):
    with open(file_path, "rb", 0) as f:
        f.seek(-(128+227), 2)         # go to the (128+227)th byte before the end
        tagx_data = f.read(227)  # read the 227 bytes that would make up the extended id3v1 tag.
        tag_data  = f.read(128)  # read the final 128 bytes that would make up the id3v1 tag.
        
        # see what juicy goodies we have.
        if tag_data[:3] == "TAG":
            # either id3 v1.0 or v1.1
            title  = strip_null_bytes(tag_data[ 3:33])
            artist = strip_null_bytes(tag_data[33:63])
            album  = strip_null_bytes(tag_data[63:93])
            year = 0
            if tag_data[93:97] != "\00\00\00\00":
                year = int(strip_null_bytes(tag_data[93:97]))
            genre  = ord(tag_data[127])
            if ord(tag_data[125]) == 0 and ord(tag_data[126]) != 0:
                # id3 v1.1
                comment = strip_null_bytes(tag_data[97:125])
                track_number = ord(tag_data[126])
                print "ID3v1.1   tag found: '%s' - '%s' by '%s' in %d, track %d, genre %d" % (title, album, artist, year, track_number, genre)
            else:
                # id3 v1.0
                comment = strip_null_bytes(tag_data[97:127])
                print "ID3v1.0   tag found: '%s' - '%s' by '%s' in %d, genre %d" % (title, album, artist, year, genre)
            # check for extended tag and, if found, add its stuff to the data.
            if tagx_data[:4] == "TAG+":
                title  += strip_null_bytes(tagx_data[  4: 64])
                artist += strip_null_bytes(tagx_data[ 64:124])
                album  += strip_null_bytes(tagx_data[124:184])
        else:
            print "No ID3v1 tag found."


# Writes the ID3v1.1 tag to a file (overwriting if present, appending if not).
def write_id3_v1_tag (input_file_path, output_song_data, output_file_path=""):
    global force_mode
    
    # if no output_file_path is given set it to the input_file_path (i.e. rewrite the input's tag).
    if output_file_path == "":
        output_file_path = input_file_path
    if output_file_path == input_file_path and not force_mode:
        raise Exception("write_id3_v1_tag called and instructed to write over the file, however force mode (-f) is not enabled.")
    
    # read the entire input file in.
    with open(input_file_path, "rb") as f:
        track_data = f.read()
    
    # check what existing id3v1 tag we have (if any), and if so purge it.
    if track_data[-128:-125] == "TAG":                      # check for v1.0/v1.1
        if track_data[-(128+227):-(128+227-4)] == "TAG+":   # check for v1.0 extended
            track_data = track_data[:-(128+227)]
        else:
            track_data = track_data[:-128]
    
    # create our new id3v1.1 tag and add it to the track data.
    genre = 255
    if output_song_data.album_year == 0:
        year_string = '\00' * 4
    else:
        year_string = str(output_song_data.album_year)
    # 3 B header, 30 B title, artist, album, 4 B year string, 28 B comment, zero-byte (signifying v1.1), 1 B track, 1 B genre
    new_tag = "TAG" + pack_null_bytes(output_song_data.track_name,  30) \
                    + pack_null_bytes(output_song_data.artist_name, 30) \
                    + pack_null_bytes(output_song_data.album_name,  30) \
                    + year_string                                       \
                    + '\00' * 28                                        \
                    + '\00'                                             \
                    + chr(output_song_data.track_number)                \
                    + chr(genre)                                        
    print "created new tag, size " + str(len(new_tag)) + " bytes"
    track_data += new_tag
    
    # write the result to the output file.
    with open(output_file_path, "wb") as f:
        f.write(track_data)


# Reads the ID3v2 tag data from a file (if present).
def read_id3_v2_tag (file_path):
    with open(file_path, "rb", 0) as f:
        header_data = f.read(10)
        
        # see what juicy goodies we have
        if header_data[:3] == "ID3":
            # check its not messed up
            if ord(header_data[3]) == 0xFF or ord(header_data[4]) == 0xFF or ord(header_data[6]) >= 0x80 or ord(header_data[7]) >= 0x80 or ord(header_data[8]) >= 0x80 or ord(header_data[9]) >= 0x80:
                print "corrupted tag found, exitting."
                return
            # Collect the tag header info. The tag_size is the complete ID3v2 tag size, minus the 
            # header (but not the extended header if one exists). Thus tag_size = total_tag_size - 10.
            tag_size = (ord(header_data[6]) << 21) + (ord(header_data[7]) << 14) + (ord(header_data[8]) << 7) + (ord(header_data[9]))
            #print "found ID3v2.%d.%d tag (size %d bytes)" % (ord(header_data[3]), ord(header_data[4]), tag_size)
            version_string = "ID3v2.%d.%d" % (ord(header_data[3]), ord(header_data[4]))
            
            # Read the frames
            total_read_size = 10
            album = ""
            title = ""
            artist = ""
            track_number = ""
            year = ""
            while (total_read_size < tag_size+10):
                # Collect the frame header info. the frame_size is the size of the frame, minus the
                # header. Thus frame_size = total_frame_size - 10.
                f.seek(total_read_size, 0)
                frame_header_data = f.read(10)
                if frame_header_data[0] == '\00':
                    # If we have read a null byte we have reached the end of the ID3 tag. It turns 
                    # out the majority of ID3 tags are heavily padded and are actually significantly 
                    # longer than it needs to be so that editors can modify it without having to 
                    # rewrite the entire MP3 file. This is poorly documented and, to me, really 
                    # arcane - I can't see why you would want to avoid having to rewrite the whole 
                    # file. The ID3 tags I have tested are typically between 500 and 1000 bytes 
                    # while around 4200 bytes is actually allocated.
                    break
                frame_id = frame_header_data[0:4]
                frame_size = (ord(frame_header_data[4]) << 24) + (ord(frame_header_data[5]) << 16) + (ord(frame_header_data[6]) << 8) + (ord(frame_header_data[7]))
                #print "  Frame ID: %s, size %d bytes" % (frame_id, frame_size)
                total_read_size += 10 + frame_size
                # Collect frame info
                if frame_id == "TALB":
                    album = f.read(frame_size)[1:]
                elif frame_id == "TIT2":
                    title = f.read(frame_size)[1:]
                elif frame_id == "TPE1":
                    artist = f.read(frame_size)[1:]
                elif frame_id == "TRCK":
                    track_number = int(f.read(frame_size)[1:].split('/')[0])
                elif frame_id == "TYER":
                    year = int(f.read(frame_size)[1:])
            print "%s tag found: '%s' - '%s' by '%s' in %d, track %d" % (version_string, title, album, artist, year, track_number)
        else:
            print "No ID3v2 tag found."


# Writes the ID3v2.x tag to a file (overwriting if present, inserting if not).
def write_id3_v2_tag (input_file_path, output_song_data, output_file_path=""):
    global force_mode
    
    # if no output_file_path is given set it to the input_file_path (i.e. rewrite the input's tag).
    if output_file_path == "":
        output_file_path = input_file_path
    if output_file_path == input_file_path and not force_mode:
        raise Exception("write_id3_v2_tag called and instructed to write over the file, however force mode (-f) is not enabled.")
    
    # read the entire input file in.
    with open(input_file_path, "rb") as f:
        track_data = f.read()
    
    # check what existing id3v2 tag we have (if any), and if so purge it.
    if track_data[:3] == "ID3":
        # check its not messed up
        if ord(track_data[3]) == 0xFF or ord(track_data[4]) == 0xFF or ord(track_data[6]) >= 0x80 or ord(track_data[7]) >= 0x80 or ord(track_data[8]) >= 0x80 or ord(track_data[9]) >= 0x80:
            raise Exception("write_id3_v2_tag called on a file with a corrupted id3v2 tag, meaning the tag size cannot be easily calculated. Exitting.")
        # Collect the tag header info. The tag_size is the complete ID3v2 tag size, minus the 
        # header (but not the extended header if one exists). Thus tag_size = total_tag_size - 10.
        tag_size = (ord(track_data[6]) << 21) + (ord(track_data[7]) << 14) + (ord(track_data[8]) << 7) + (ord(track_data[9]))
        tag_data   = track_data[:tag_size+10]
        track_data = track_data[tag_size+10:]
    
    # cut the bits that we are going to replace out of the old tag (thus keeping previous tag frames an
    # important consideration as some programs (i.e. windows media player) store their own data in them).
    total_read_size = 10
    new_tag = ""
    while (total_read_size < tag_size+10):
        if tag_data[total_read_size] == '\00':
            break
        frame_id = tag_data[total_read_size:total_read_size+4]
        frame_size = (ord(tag_data[total_read_size+4]) << 24) + (ord(tag_data[total_read_size+5]) << 16) + (ord(tag_data[total_read_size+6]) << 8) + (ord(tag_data[total_read_size+7]))
        if frame_id != "TALB" and frame_id != "TIT2" and frame_id != "TPE1" and frame_id != "TRCK" and frame_id != "TYER":
            new_tag += tag_data[total_read_size:total_read_size+10+frame_size]
        total_read_size += 10 + frame_size
    
    # add the new data into the tag
    
    # write to the output file


# for all words in the list, replace all but the last '.', all '_' and '-' with spaces, then remove 
# duplicate spaces before finally fixing the capitalisation.
def clean_string (s):
    # replace any of '.-_' with spaces (minus the last . for file extension).
    if s[-4:] == ".mp3":
        number_of_dots = s.count(".")
        s = s.replace('.', ' ', number_of_dots-1)
    else:
        s = s.replace('.', ' ')
    s = s.replace('-', ' ')
    s = s.replace('_', ' ')
    
    # lower the case.
    s = s.lower()
    
    # split the string into words (has the side effect of removing duplicate spaces).
    words = s.split()
    
    # fix the capitalisation.
    for i in range(len(words)):
        if i == 0 or (words[i] != "and" and words[i] != "at" and words[i] != "of" and words[i] != "or" and words[i] != "the"):
            words[i] = words[i][0].upper() + words[i][1:]
    
    # recombine the words into a string.
    s = " ".join(words)
    
    return s


# Removes the words repeated in the same place in the strings in the list. This is necessary in the
# context of song filenames to undo filenames which include the artist or album name.
def remove_common_words (string_list):
    number_of_strings = len(string_list)
    
    # split each of the strings in the list into a list of words.
    word_list = []
    for i in range(number_of_strings):
        word_list.append(string_list[i].split())
    
    # calculate the number of words in the shortest string.
    len_shortest_string = len(word_list[0])
    for i in range(1, number_of_strings):
        if len(word_list[i]) < len_shortest_string:
            len_shortest_string = len(word_list[i])
    
    # for each of the possible shared words in the strings, check the words against the first word
    # for repetition, removing any that appear in the same place in every word (though only if the
    # run is at the start of the string (or 1 indented)).
    for i in range(len_shortest_string):
        exitted_early = 0
        for j in range(1, number_of_strings):
            if word_list[0][i] != word_list[j][i]:
                exitted_early = 1
                break
        if exitted_early == 0:
            for k in range(number_of_strings):
                word_list[k][i] = ""
        elif i > 0:
            break
    
    # recombine the word lists into a list of strings and return (removing additional spaces).
    return_list = []
    for i in range(number_of_strings):
        return_list.append(word_list[i][0])
        #string_list[i] = word_list[i][0]
        
        previous_blank = 0
        if (word_list[i][0] == ""):
            previous_blank = 1
        
        for j in range(1, len(word_list[i])):
            if previous_blank == 0:
                #string_list[i] += " "
                return_list[i] += " "
            #string_list[i] += word_list[i][j]
            return_list[i] += word_list[i][j]
            
            previous_blank = 0
            if word_list[i][j] == "":
                previous_blank = 1
    
    #return string_list
    return return_list


# cleans all the files given to it (the cleaning only really makes sense per album folder).
def clean_folder (file_list):
    # create a cleaned copy of the file list
    cleaned_file_list = []
    for f in file_list:
        cleaned_file_list.append(clean_string(f))
    # remove the common words
    if len(file_list) > 1:
        cleaned_file_list = remove_common_words(cleaned_file_list)
    return cleaned_file_list




#-----------------------------------------------------------------------#
#---------------------------    MAIN CODE    ---------------------------#
#-----------------------------------------------------------------------#
# Parse command line arguments
verbose_mode = False
force_mode   = False
base_folder  = ""
if len(sys.argv) > 1:
    base_folder = sys.argv[1]
    for i in range(2, len(sys.argv)):
        if sys.argv[i] == '-v':
            verbose_mode = True
        elif sys.argv[i] == '-f':
            force_mode = True
# check for a valid input
if (base_folder == ""):
    print "Error: The program must be run on a folder, with the form:\n./music_tagger FOLDER [-f] [-v]\n  -f - write changes.\n  -v - verbose mode.\nSystem exiting."
    sys.exit()

# traverse all folders (dirname gives the path to the current directory, dirnames gives the list of
# subdirectories in the folder, filenames gives the list of files in the folder).
#print "--------------------"
walk_results = os.walk(base_folder)
#wr1, wr2, wr3 = walk_results
"""
print "1------"
for dirname, dirnames, filenames in walk_results:
    print "directory: " + dirname
    print "  subdirectories:"
    for subdirname in dirnames:
        print "    " + os.path.join(dirname, subdirname)
    print "  files:"
    for filename in filenames:
        print "    " + os.path.join(dirname, filename)
print "-------"


# clean lol
print "2------"
walk_results = os.walk(base_folder)
#for dirname, dirnames, filenames in wr1, wr2, wr3:
for dirname, dirnames, filenames in walk_results:
    filenames = clean_folder(filenames)
    print filenames
print "-------"
"""
# print lol
#print "------DIRECTORY CONTENTS------"
#for dirname, dirnames, filenames in wr1, wr2, wr3:
#    print "  ----------------------------"
#    for subdirname in dirnames:
#        print "  +" + subdirname
#    for filename in filenames:
#        print "  -" + filename
#print "------------------------------"


# build internal data for each file (from file system + id3 tags)
print "3------"
#walk_results = 
#for dirname, dirnames, filenames in wr1, wr2, wr3:
for dirname, subdirnames, filenames in os.walk(base_folder):
    song_list = []
    cleaned_filenames = clean_folder(filenames)
    for i in range(len(filenames)):
        if filenames[i][-4:] == ".mp3":
            # BOYZ WE FOUND OURSELF A SONG. Lets index him.
            file_path = os.path.join(dirname, filenames[i])
            new_song = MusicFile(file_path, cleaned_filenames[i])
            song_list.append(new_song)
            print "Created: " + str(new_song)
            read_id3_v1_tag(file_path)
            read_id3_v2_tag(file_path)
            #print "writing to " + file_path
            #new_song.track_name = "lol dis is a song"
            #new_song.track_number = 3
            #write_id3_v1_tag(file_path, new_song, file_path+".mp3")
            write_id3_v2_tag(file_path, new_song, file_path+".mp3")
            print ""
print "-------"

# write the newly corrected data back to the tags

# write new data to file system

stringy = []
stringy.append("the giant BOB.-of______joNES.mpz")
stringy.append("THE.giant man.oF.the.month.avi")
stringoo = []
stringoo.append(clean_string(stringy[0]))
stringoo.append(clean_string(stringy[1]))
strings = remove_common_words(stringoo)
print stringy[0]
print stringy[1]
print stringoo[0]
print stringoo[1]
print strings[0]
print strings[1]

#x = Song("boo")

print "Finished."
