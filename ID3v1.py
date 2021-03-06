"""Imports:
    TrackData: for containing the extracted information
"""
import TrackData


def _strip_null_bytes(data):
    """Strips extraneous whitespace and null bytes from data to give a string.

    Args:
        data: The raw string data to process.

    Returns:
        The stripped string.
    """
    return data.replace("\00", "").strip()


def _pack_null_bytes(string, length):
    """Packs a string into a given number of bytes and null terminates it.

    This is achieved either by truncating (when too long) or adding null bytes
    (when too short).

    Args:
        string: The string to pack. May be None.
        length: The number of bytes to pack to.

    Returns:
        A packed string of the requested number of bytes.
    """
    if string:
        if len(string) >= length-1:
            data = string[:length-1] + '\00'
        else:
            data = string + ('\00' * (length - len(string)))
    else:
        data = '\00' * length
    return data


class _Tag(object):
    """ID3v1 tag

    Attributes:
        version: int major version number (e.g. 0 for ID3v1.0)
        data: TrackData from this header
        comment: string tag comment
        genre: int track genre (non standard)
        is_extended: boolean representing whether or not parsed tag had an
            extended tag
    """
    def __init__(self, header_data, xheader_data):
        """Interprets byte data as a tag header to build object

        Args:
            header_data: character array of bytes representing the tag header.
                Must contain an ID3v1 tag
            xheader_data: character array of bytes representing the extended tag
                header. This does not have to contain an extended header (in
                which case it will be ignored).
        """
        # Check we're actually looking at an ID3v1 tag
        if header_data[:3] != "TAG":
            raise Exception("Given data does not contain an ID3v1 tag header")
        # Extract data
        self.data = TrackData.TrackData()
        self.data.title = _strip_null_bytes(header_data[3:33])
        self.data.artist = _strip_null_bytes(header_data[33:63])
        self.data.album = _strip_null_bytes(header_data[63:93])
        self.data.year = TrackData.mint(_strip_null_bytes(header_data[93:97]))
        if ord(header_data[125]) == 0 and ord(header_data[126]) != 0:
            self.version = 1    # id3 v1.1
            self.comment = _strip_null_bytes(header_data[97:125])
            self.data.track = ord(header_data[126])
        else:
            self.version = 0    # id3 v1.0
            self.comment = _strip_null_bytes(header_data[97:127])
            self.data.track = None
        self.genre = ord(header_data[127])
        # Check if we have an extended tag and extract it
        self.is_extended = xheader_data[:4] == "TAG+"
        if self.is_extended:
            self.data.title += _strip_null_bytes(xheader_data[4:64])
            self.data.artist += _strip_null_bytes(xheader_data[64:124])
            self.data.album += _strip_null_bytes(xheader_data[124:184])

    def __str__(self):
        """Override string printing method"""
        return "ID3v1.%d%s" % (self.version, '+' if self.is_extended else '')

    def get_data(self):
        """Extracts TrackData from this tag

        Returns:
            TrackData with this tag's raw data
        """
        return self.data


def calculate_tag_size(file_handle):
    """Calculates the size of an ID3v1 tag

    Args:
        file_handle: a file handle opened in a readable binary mode

    Returns:
        int number of bytes in the tag, or 0 if the file does not have one
    """
    # Read the standard and extended tag headers
    cursor_pos = file_handle.tell()
    file_handle.seek(-(128+227), 2)
    tagx_header = file_handle.read(4)
    file_handle.seek(-128, 2)
    tag_header = file_handle.read(3)
    file_handle.seek(cursor_pos, 0)
    # Calculate tag size
    if tag_header == "TAG":
        if tagx_header == "TAG+":
            return 128+227
        return 128
    return 0


def read_tag_data(file_path):
    """Reads the ID3v1 tag data from a file (if present).

    ID3 v1.0 and v1.1 tags are supported along with extended tags.

    Args:
        file_path: String path to the file to read the tag from.

    Returns:
        A TrackData with the fields initialised to the data read from the tag.
        Non-present fields will be initialised to None. If no valid tag exists
        None will be returned.
    """
    with open(file_path, "rb", 0) as f:
        # Go to the (128+227)th byte before the end.
        f.seek(-(128+227), 2)
        # Read the 227 bytes that would make up the extended id3v1 tag.
        tagx_data = f.read(227)
        # Read the final 128 bytes that would make up the id3v1 tag.
        tag_data = f.read(128)
        has_tag = tag_data[:3] == "TAG"
        # If we don't have a tag, drop out
        if not has_tag:
            return None
        # Parse the tag
        tag = _Tag(tag_data, tagx_data)
        data = tag.get_data()
        # clean the strings generated
        data.clean(False)
        return data
    return None


def create_tag_string(data):
    """ Converts the given TrackData into a ID3v1.1 tag.

    Args:
        data: A TrackData object whose data will be put into the tag.

    Returns:
        A string of the correct byte length representing the ID3v1.1 tag.
    """
    if data.year:
        year_string = str(data.year)
    else:
        year_string = '\00' * 4
    # 3 B header, 30 B title, 30 B artist, 30 B album, 4 B year string,
    # 28 B comment, zero-byte (signifying v1.1), 1 B track, 1 B genre
    new_tag = "TAG"                             \
            + _pack_null_bytes(data.title, 30)  \
            + _pack_null_bytes(data.artist, 30) \
            + _pack_null_bytes(data.album, 30)  \
            + year_string                       \
            + '\00' * 28                        \
            + '\00'                             \
            + chr(data.track)                   \
            + chr(data.genre)
    return new_tag
