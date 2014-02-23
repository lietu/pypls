import argparse
import logging
import os
import platform
import sys
import time


def _get_log():
    """Set up logging with some decent output format"""

    logger = logging.getLogger('PyPLS')
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s [%(levelname)8s] %(message)s')
    ch.setFormatter(formatter)

    logger.addHandler(ch)

    return logger

log = _get_log()
fsenc = sys.getfilesystemencoding()

# First ~3 encodings should be more than enough, but I put all of these in
# just in case it ever proves to be helpful for any usecase
encodings = (
    fsenc, "latin_1", "utf_8", "cp850", "ascii", "big5", "big5hkscs", "cp037",
    "cp424", "cp437", "cp500", "cp720", "cp737", "cp775", "cp852", "cp855",
    "cp856", "cp857", "cp858", "cp860", "cp861", "cp862", "cp863", "cp864",
    "cp865", "cp866", "cp869", "cp874", "cp875", "cp932", "cp949", "cp950",
    "cp1006", "cp1026", "cp1140", "cp1250", "cp1251", "cp1252", "cp1253",
    "cp1254", "cp1255", "cp1256", "cp1257", "cp1258", "euc_jp", "euc_jis_2004",
    "euc_jisx0213", "euc_kr", "gb2312", "gbk", "gb18030", "hz", "iso2022_jp",
    "iso2022_jp_1", "iso2022_jp_2", "iso2022_jp_2004", "iso2022_jp_3",
    "iso2022_jp_ext", "iso2022_kr", "iso8859_2", "iso8859_3", "iso8859_4",
    "iso8859_5", "iso8859_6", "iso8859_7", "iso8859_8", "iso8859_9",
    "iso8859_10", "iso8859_13", "iso8859_14", "iso8859_15", "iso8859_16",
    "johab", "koi8_r", "koi8_u", "mac_cyrillic", "mac_greek", "mac_iceland",
    "mac_latin2", "mac_roman", "mac_turkish", "ptcp154", "shift_jis",
    "shift_jis_2004", "shift_jisx0213", "utf_32", "utf_32_be", "utf_32_le",
    "utf_16", "utf_16_be", "utf_16_le", "utf_7", "utf_8_sig", "idna"
)


class InvalidEntryError(Exception):
    pass


class PlaylistGenerator(object):
    """Generator for looping through playlist items"""

    def __init__(self, source):
        """Initialize generator variables"""

        self.basepath = os.path.dirname(source)
        self.encoding_stats = {}
        self.file = open(source, 'rb')
        self.first_line = True
        self.is_windows = (platform.system() == "Windows")
        self.source = source
        self.errors = 0

    def __del__(self):
        """Clean up once this generator is thrown away"""

        if self.file:
            self.file.close()

    def __iter__(self):
        """Get the iterator for this generator"""

        return self

    def __next__(self):
        """Python 3 compatibility"""

        return self.next()

    def _clean_line(self, line):
        """Clean up a read line from extra junk"""

        # Trailing and leading whitespace, e.g. \n
        line = line.strip()

        # Check for UTF-8 BOM
        if self.first_line:
            self.first_line = False
            if line[0] == 65279:
                line = line[1:]

        return line

    def _get_path(self, entry):
        """Try our best to parse a full path to file from the given entry"""

        fullpath = None
        for enc in encodings:
            try:
                tmp = entry.decode(enc)

                # Support relative entries starting with \
                if self.is_windows and tmp.startswith("\\"):
                    test = os.path.join(self.basepath.split('\\')[0], tmp)
                else:
                    test = os.path.join(self.basepath, tmp)
            except UnicodeDecodeError:
                continue

            # Convert Windows paths to *nix paths and vice-versa
            if self.is_windows:
                test = test.replace('/', '\\')
            else:
                test = test.replace('\\', '/')

            if os.path.exists(test):
                fullpath = test

                # Record matched encodings for development purposes
                if not enc in self.encoding_stats:
                    self.encoding_stats[enc] = 0
                self.encoding_stats[enc] += 1

                break

        if fullpath is None:
            self.errors += 1
            raise InvalidEntryError("Failed to find entry {}".format(entry))

        return fullpath

    def next(self):
        """Get next entry in the playlist"""

        raise NotImplementedError("You should implement this function")


class M3UPlaylist(PlaylistGenerator):
    """M3U and M3U8 format playlist handler"""

    def __init__(self, source):
        """Initialize generator variables"""

        super(M3UPlaylist, self).__init__(source)

        # Python 3 compatibility
        if bytes.__name__ == "bytes":
            self.comment = bytes('#', 'utf8')
        else:
            self.comment = "#"

    def next(self):
        """Get next entry in the playlist"""

        for line in self.file:
            try:
                line = self._clean_line(line)

                # Skip comment entries
                if not line.startswith(self.comment):
                    return self._get_path(line)
            except InvalidEntryError as e:
                log.error(e)

        raise StopIteration


class PLSPlaylist(PlaylistGenerator):
    """PLS format playlist handler"""

    def __init__(self, source):
        """Initialize generator variables"""

        super(PLSPlaylist, self).__init__(source)

        # Python 3 compatibility
        if bytes.__name__ == "bytes":
            self.equals = bytes('=', 'utf8')
            self.prefix = bytes('File', 'utf8')
        else:
            self.equals = '='
            self.prefix = 'File'

    def next(self):
        """Get next entry in the playlist"""

        for line in self.file:
            try:
                line = self._clean_line(line)
                pos = line.find(self.equals)
                # Search for entries that look like: File=path\to\file
                if line.startswith(self.prefix) and pos >= 0:
                    return self._get_path(line[pos + 1:])
            except InvalidEntryError as e:
                log.error(e)

        raise StopIteration


def getPlaylistGenerator(source):
    """Figure out which playlist generator to use, and return it"""

    __, ext = os.path.splitext(source)
    ext = ext.lower()

    if ext == ".m3u" or ext == ".m3u8":
        return M3UPlaylist(source)
    elif ext == ".pls":
        return PLSPlaylist(source)

    raise ValueError("Unsupported playlist {}".format(source))


class PyPLS(object):
    """Playlist stats calculator main class"""

    def run(self):
        """Run the application"""

        options = self._get_options()

        # Total statistics counters
        sources = 0
        total_errors = 0
        total_files = 0
        total_size = 0
        total_start = time.time()

        for source in options.playlist:
            sources += 1

            # Per playlist stats
            files = 0
            size = 0
            start = time.time()

            log.info("Processing playlist {}".format(source))

            # Go through the playlist entries
            generator = getPlaylistGenerator(source)
            for path in generator:
                files += 1
                size += os.path.getsize(path)

            elapsed = time.time() - start

            log.info("Playlist {} processed in {:.2f} seconds".format(
                source, elapsed
            ))
            log.info("Files in list : {}".format(files))
            log.info("Playlist size : {}".format(self._format_size(size)))
            log.info("Errors in file: {}".format(generator.errors))

            total_errors += generator.errors
            total_files += files
            total_size += size

        if sources > 0:
            elapsed = time.time() - total_start
            log.info("Total time elapsed: {:.2f} seconds".format(elapsed))
            log.info("Total files : {}".format(total_files))
            log.info("Total size  : {}".format(self._format_size(total_size)))
            log.info("Total errors: {}".format(total_errors))

    def _get_options(self):
        """Get the options for the application"""

        parser = argparse.ArgumentParser(
            description='Calculate disk space etc. stats from playlist files'
        )

        parser.add_argument(
            'playlist', metavar='PATH', type=str, nargs='+',
            help='Path to playlists to process'
        )

        args = parser.parse_args()

        return args

    def _format_size(self, size):
        """Format bytes to a human readable string"""

        for suffix in ['B', 'kB', 'MB', 'GB', 'TB', 'PB']:
            if size < 1024.0:
                return "{:.2f} {}".format(size, suffix)
            size /= 1024.0


if __name__ == "__main__":
    pypls = PyPLS()
    pypls.run()
