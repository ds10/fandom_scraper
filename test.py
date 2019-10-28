#fucking pycurl on 3.7
import wptools

so = wptools.page('Stack Overflow').get_parse()
so.infobox
