#!/usr/bin/env python

import sys
import os
import requests
import json

if not os.path.exists ('json'):
    os.mkdir ('json')


def dumpjson (d, hint):
    icount = hint+1
    while True:
        fname = f'json/{icount:08}.json'
        if os.path.exists (fname):
            icount += 1
            continue
        json.dump (d, open (fname, 'w'))
        break
    return icount
    

def get_item_json(url, items=[], conditional='True', jsonhint = 0, npage=50):
    # Check that the query URL is not an item or resource link.
    exclude = ["loc.gov/item","loc.gov/resource"]
    if any(string in url for string in exclude):
        raise NameError('Your URL points directly to an item or '
                        'resource page (you can tell because "item" '
                        'or "resource" is in the URL). Please use '
                        'a search URL instead. For example, instead '
                        'of \"https://www.loc.gov/item/2009581123/\", '
                        'try \"https://www.loc.gov/maps/?q=2009581123\". ')

    # request pages of npage results at a time
    params = {"fo": "json", "c": npage, "at": "results,pagination"}
    call = requests.get(url, params=params)
    # Check that the API request was successful
    if (call.status_code==200) & ('json' in call.headers.get('content-type')):
        print (call.status_code)
        data = call.json()
        results = data['results']
        for result in results:
            # Filter out anything that's a colletion or web page
            filter_out = ("collection" in result.get("original_format")) \
                    or ("web page" in result.get("original_format")) \
                    or (eval(conditional)==False)
            if not filter_out:
                # Get the link to the item record
                if result.get("id"):
                    item = result.get("id")
                    print (item, type(result))
                    jsonhint = dumpjson (result, jsonhint)
                    # Filter out links to Catalog or other platforms
                    if item.startswith("http://www.loc.gov/resource"):
                      resource = item  # Assign item to resource
                      items.append(resource)
                    if item.startswith("http://www.loc.gov/item"):
                        items.append(item)
        # Repeat the loop on the next page, unless we're on the last page.
        if data["pagination"]["next"] is not None:
            next_url = data["pagination"]["next"]
            get_item_json(next_url, items, conditional, jsonhint = jsonhint, npage=npage)

        return items
    else:
            print('There was a problem. Try running the cell again, or check your searchURL.')
    return


query = sys.argv[1]
ids = get_item_json (query, items = [])

print(f'Got {len(ids)} pages')
