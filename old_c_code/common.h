/*-----------------------------------------------------------------------*/
/*----------------------------    LICENSE    ----------------------------*/
/*-----------------------------------------------------------------------*/
/* This file is part of the music_tagger program                         */
/* (https://github.com/jonsim/music_tagger).                             */
/*                                                                       */
/* Foobar is free software: you can redistribute it and/or modify        */
/* it under the terms of the GNU General Public License as published by  */
/* the Free Software Foundation, either version 3 of the License, or     */
/* (at your option) any later version.                                   */
/*                                                                       */
/* Foobar is distributed in the hope that it will be useful,             */
/* but WITHOUT ANY WARRANTY; without even the implied warranty of        */
/* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         */
/* GNU General Public License for more details.                          */
/*                                                                       */
/* You should have received a copy of the GNU General Public License     */
/* along with Foobar.  If not, see <http://www.gnu.org/licenses/>.       */
/*-----------------------------------------------------------------------*/


/*-----------------------------------------------------------------------*/
/*----------------------------     ABOUT     ----------------------------*/
/*-----------------------------------------------------------------------*/
/* A small program to tidy music files. It recursively explores a given  */
/* directory and standardises folder structures, file naming conventions */
/* and ID3 tags.                                                         */
/* Author: Jonathan Simmonds                                             */
/*-----------------------------------------------------------------------*/


int containsCharacter (char* s, char c, int len);
void charCopy (char* out, char* in, int len);

void replaceCharacter (char* s, char c, char remove_all_but_last_character);
void removeDuplicateSpaces (char* s);
void fixCapitals (char* s);
