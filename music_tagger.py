#!/usr/bin/python

#-----------------------------------------------------------------------#
#----------------------------    LICENSE    ----------------------------#
#-----------------------------------------------------------------------#
# This file is part of the music_tagger program                         #
# (https://github.com/jonsim/music_tagger).                             #
#                                                                       #
# music_tagger is free software: you can redistribute it and/or modify  #
# it under the terms of the GNU General Public License as published by  #
# the Free Software Foundation, either version 3 of the License, or     #
# (at your option) any later version.                                   #
#                                                                       #
# music_tagger is distributed in the hope that it will be useful,       #
# but WITHOUT ANY WARRANTY; without even the implied warranty of        #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
# GNU General Public License for more details.                          #
#                                                                       #
# You should have received a copy of the GNU General Public License     #
# along with music_tagger.  If not, see <http://www.gnu.org/licenses/>. #
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
"""Imports:
    sys: console output
    os: walking the directory structure
    Config: handling program config options from files or command line args
    TrackData: storing data from a single source about a track
    TrackFile: collecting all a track's TrackData together
    TrackCollection: collecting all TrackFiles under in the searched directory
    Progress: formatting progress messages
"""
import sys
import os
import Config
import TrackData
import TrackFile
import TrackCollection
import Progress
# This project makes use of the Levenshtein Python extension for string
# comparisons (edit distance and the like - used for fixing inconsistently
# named files). A copy of it is provided with this project, and the most
# recent version or more up to date information can be found at the
# project page: http://code.google.com/p/pylevenshtein/
# To install, simply navigate to the python-Levenshtein-0.10.1 directory
# and run the command:
# python setup.py install
# NB: This requires that the 'python-dev' package is installed.


# Progress reporting string constants.
SEARCHING_STATUS_STRING = '[1/5] Searching file structure'
INDEXING_STATUS_STRING = '[2/5] Indexing tracks'
PROCESSING_STATUS_STRING = '[3/5] Processing indexed tracks'
STANDARDISING_STATUS_STRING = '[4/5] Standardising track data'
REWRITING_STATUS_STRING = '[5/5] Rewriting tracks'



#-----------------------------------------------------------------------#
#-------------------    STRING HANDLING FUNCTIONS    -------------------#
#-----------------------------------------------------------------------#

class CleanFilename(object):
    """A tuple of cleaned filename and the original

    Attributes:
        original: string original filename
        cleaned: string post-processed filename"""
    def __init__(self, filename):
        self.original = filename
        self.cleaned = TrackData.clean_string(filename, True)


def remove_common_words(file_list):
    """ Removes words repeated in the same place in all filenames in a list.

    This is necessary in the context of song filenames to undo filenames which
    include the artist or album name.

    Args:
        file_list: list of CleanFilename to mp3s. The cleaned field will be used
            for comparison. The list is modified in place.

    Returns:
        A list of CleanFilenames with the common words removed.
    """
    def _remove_common_words(word_list, word_count, file_count, forwards, max_indent):
        """Passes through a list of list of words and removes duplicates

        Args:
            word_list: list of list of strings to remove common words from
            word_count: int number of words to check up to
            file_count: int number of list of words to check up to
            fowards: boolean, True to scan through the words forwards (aligning
                all filenames on word[0] and checking incrementally from there)
                or False to scan backwards (aligning all filenames on word[-1]
                and checking decrementally from there)
            max_indent: int maximum word position which may be passed over if it
                does not match all files without being removed. Positive int, 0
                for no indent (i.e. break immediately)
        """
        if forwards:
            word_scan_order = range(word_count)
        else:
            word_scan_order = range(-1, -word_count-1, -1)
            # L[0] is 1st element forwards while L[-1] is 1st element backwards
            max_indent += 1
        # For each of the possible shared words in the strings, check against
        # the first word for repetition, removing any that appear in the same
        # place in every word. The run must be at the start (forwards) or end
        # (backwards) of the string, or up to max_indent offset from the start
        # (forwards) or end (backwards).
        for word_idx in word_scan_order:
            all_words_match = True
            for file_idx in range(1, file_count):
                if word_list[0][word_idx] != word_list[file_idx][word_idx]:
                    all_words_match = False
                    break
            if all_words_match:
                for file_idx in range(file_count):
                    word_list[file_idx][word_idx] = ''
            elif abs(word_idx) >= max_indent:
                break

    # Split each of the strings in the list into a list of words (ignoring the
    # last 4 characters which will be .mp3)
    word_list = [f.cleaned[:-4].split() for f in file_list]

    # Calculate the number of words in the shortest string.
    len_shortest_string = len(min(word_list, key=len))
    file_count = len(file_list)
    # Remove all matching words from the start of the filenames (or 1 offset)
    _remove_common_words(word_list, len_shortest_string, file_count, True, 1)
    # Remove all matching words from the end of the filenames
    _remove_common_words(word_list, len_shortest_string, file_count, False, 0)

    # Recombine the words for each file into a single name (removing additional
    # spaces), re-add the .mp3 and overwrite the cleaned field.
    for i in range(file_count):
        file_list[i].cleaned = ' '.join([(w) for w in word_list[i] if w]) + '.mp3'

    return file_list


def extract_mp3s_and_clean(file_list):
    """Extracts all mp3s from a filelist and and removes common words from them

    Args:
        file_list: list of strings representing filenames

    Returns:
        A list of mp3 CleanFilenames. May be empty if no mp3s were found
    """
    file_list = [f for f in file_list if f[-4:].lower() == '.mp3']
    if not file_list:
        return []
    cleaned_file_list = [(CleanFilename(f)) for f in file_list]
    return remove_common_words(cleaned_file_list)


# takes the supplied base folder file path and generates a filepath of a new folder in the directory
# below it
def generate_new_filepath(target_file_path):
    # get the absolute file path (use realpath rather than abspath to accomodate symlinks).
    abs_path = os.path.normpath(os.path.realpath(target_file_path))
    abs_path_split = os.path.split(abs_path)

    # check we can go down a level
    if abs_path_split[0] == '' or abs_path_split[1] == '':
        raise Exception("ERROR: You cannot ask the program to process the entire "
                        "file system, please be more specific.")

    # generate the path of the next level down
    new_path = os.path.join(abs_path_split[0], 'music_tagger_output')
    if os.path.isdir(new_path):
        i = 1
        while os.path.isdir(new_path + str(i)):
            i += 1
        new_path += str(i)
    return new_path


def print_warnings(warnings):
    """Outputs all warnings and clears the list

    Args:
        warnings: list of string warnings to print. This list will be cleared
            once printed.

    Returns:
        None
    """
    for warning in warnings:
        sys.stdout.write("WARNING: %s\n" % (warning))
    del warnings[:]


#-----------------------------------------------------------------------#
#---------------------------    MAIN CODE    ---------------------------#
#-----------------------------------------------------------------------#
def main():
    """Main function"""
    # Build program config from command line and config file.
    config = Config.Config()

    warnings = []

    # Recursively tranverse from the provided root directory looking for mp3s:
    #  * dirname gives the path to the current directory
    #  * dirnames gives the list of subdirectories in the folder
    #  * filenames gives the list of files in the folder
    Progress.state(SEARCHING_STATUS_STRING)
    track_list = []
    for dirname, subdirnames, filenames in os.walk(config.directory):
        # Extract and clean filenames of all mp3s
        cleaned_mp3_filenames = extract_mp3s_and_clean(filenames)
        for f in cleaned_mp3_filenames:
            # Extract all the information possible from the song and add it.
            file_path = os.path.join(dirname, f.original)
            new_file = TrackFile.TrackFile(file_path, f.cleaned)
            track_list.append(new_file)
    track_count = len(track_list)

    # create storage system
    music_collection = TrackCollection.TrackCollection()

    # Add all located files to the collection.
    for i in range(track_count):
        track_list[i].load_all_data()
        #print track_list[i]
        track_list[i].finalise_data()
        music_collection.add(track_list[i])
        Progress.report(INDEXING_STATUS_STRING, track_count, i+1)
    print_warnings(warnings)

    # Remove all duplicate files from the collection.
    def progress_stub1(total_units, done_units):
        """Stub for encapsulating the 'processing'' formatter"""
        Progress.report(PROCESSING_STATUS_STRING, total_units, done_units)
    music_collection.remove_duplicates(warnings, progress_stub1)
    print_warnings(warnings)

    # Standardise track data on the remaining files.
    def progress_stub2(total_units, done_units):
        """Stub for encapsulating the 'standardising'' formatter"""
        Progress.report(STANDARDISING_STATUS_STRING, total_units, done_units)
    music_collection.standardise_album_tracks(warnings, progress_stub2)
    print_warnings(warnings)

    if config.verbose:
        music_collection.sort_songs_by_track()
        print music_collection

    if config.dry_run:
        Progress.skip(REWRITING_STATUS_STRING)
    else:
        print "TBD"
        # write the newly corrected data to a new file system with new tags
        #new_folder = generate_new_filepath(args.directory)
        #print "Creating new directory structure in %s." % (new_folder)
        #music_collection.create_new_filesystem(new_folder)

    # done
    print "Finished."


# Entry point.
if __name__ == "__main__":
    main()
