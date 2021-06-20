# PyPLS

Playlist Statistics tool.

PyPLS helps you check some (slightly) useful statistics about your playlist files.
These stats include how many entries there are in the file, how many of them are
erroneous, and how much disk space do all the entries take in total.

The tool should be fairly memory efficient, reading files line by line and
processing a single entry at a time. This however has not been confirmed by any
means.

Why would you want to do anything with the tool? I dunno, but I use it to check
the size of playlists I create with WinAmp before importing them to my iPod via
iTunes. Neither iTunes or WinAmp can show me the size of the playlist easily.


## Compatibility

The code runs on Windows and *nix (tested on Linux), on both Python 2.7 and 3
(dunno, and don't care about older ones). The playlist formats supported are
M3U, M3U8, and PLS. Adding support for more formats should be very easy.

## Usage

Download pypls.py or clone the repository. Then run one of the following:

```
python pypls.py --help
python pypls.py path/to/playlist.m3u
python pypls.py path/to/playlist.m3u path/to/another.pls
python pypls.py path/to/*.pls
```

# Licensing

The code is released under new BSD and MIT licenses. Basically that means you can
do whatever you want with it, as long as you don't blame me if it breaks something.
However, it really shouldn't break anything.

More details in the LICENSE.md file.


# Financial support

This project has been made possible thanks to [Cocreators](https://cocreators.ee) and [Lietu](https://lietu.net). You can help us continue our open source work by supporting us on [Buy me a coffee](https://www.buymeacoffee.com/cocreators).

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/cocreators)
