#!/usr/bin/env python

# Quick build script to assemble profiles.
#
# Lots of room to improve validation or documentation at this step, threw in
# some assertions to avoid passing malformed profiles to a driver.

import yaml
import json
import pyaml
import os
import collections

def load_encodings():
    # Load in all the encodings
    encoding_fn = os.path.dirname(__file__) + "/../data/encoding.yml"
    encodings_raw = yaml.safe_load(open(encoding_fn).read())
    return encodings_raw

def load_profiles():
    # Load in all the profiles
    profiles_raw = {}
    profiles_dir = os.path.dirname(__file__) + "/../data/profile/"
    for profile_fn in os.listdir(profiles_dir):
        profile_dict = yaml.safe_load(open(profiles_dir + profile_fn).read())
        # One item per file
        assert len(profile_dict) == 1, "{}: expected one entry, got {}".format(profile_fn, len(profile_dict))
        # Item must match filename
        profile_name, profile_val = profile_dict.popitem()
        assert profile_name + ".yml" == profile_fn, "{}: Expected to find profile named the same as file, got {}".format(profile_fn, profile_name)
        profiles_raw[profile_name] = profile_val
    return profiles_raw

def substitute_profile(profile_name, profiles_raw, encodings_raw):
    # Build stack of inheritance
    current_key = profile_name
    keys = [current_key]
    values = [profiles_raw[current_key]]
    while 'inherits' in profiles_raw[current_key]:
        assert not profiles_raw[current_key]['inherits'] in keys, "Profile {}: Circular reference calculating inheritance".format(profile_name)
        current_key = profiles_raw[current_key]['inherits']
        keys.append(current_key)
        values.append(profiles_raw[current_key])

    # Merge base profiles and sub-profiles by overriding entire keys, except for 'features' list, which are merged item-by-item. 
    profile = dict((k, v) for d in values[::-1] for k, v in d.items())
    profile['features'] = dict((k, v) for d in values[::-1] for k, v in (d['features'].items() if 'features' in d else []))
    if 'inherits' in profile:
        del profile['inherits']

    # Sanity check for required keys exist
    required_keys = ['vendor', 'features', 'media', 'notes', 'fonts', 'colors', 'codePages', 'name']
    for i in required_keys:
        assert i in profile.keys(), "{}: Profile key '{}' must be defined".format(profile_name, i)

    # Sanity check for required features exist
    required_features = ['StarCommands', 'HighDensity', 'BarcodeB', 'BitImageColumn', 'Graphics', 'QrCode', 'BitImageRaster']
    for i in required_features:
        assert i in profile['features'].keys(), "{}: Profile feature '{}' must be defined".format(profile_name, i)

    # Reference check over encodings
    for i in profile['codePages'].values():
        assert i in encodings_raw.keys(), "{}: Profile claims to support fictional encoding '{}'".format(profile_name, i)

    return profile

def filter_encodings(encodings_raw, profiles_subsituted):
    # Give everything a name if not set
    for name, encoding in encodings_raw.items():
        if not 'name' in encoding:
            encoding['name'] = name

    # Strip out un-used code pages
    unused = encodings_raw.keys()
    for profile in profiles_subsituted.values():
        used = profile['codePages'].values()
        unused = [x for x in unused if x not in used]
    return {k: v for k, v in encodings_raw.items() if k not in unused}

if __name__ == "__main__":
    encodings_raw = load_encodings();
    profiles_raw = load_profiles();
    profiles_substituted = {}
    for profile_name in profiles_raw.keys():
        profiles_substituted[profile_name] = substitute_profile(profile_name, profiles_raw, encodings_raw)
    encodings_filtered = filter_encodings(encodings_raw, profiles_substituted)

    capabilities = {'profiles': profiles_substituted, 'encodings': encodings_filtered}

    # Dump output in format that is safe for human consumption in reasonable quantities
    json_capabilities = json.dumps(capabilities, sort_keys=True, indent=4, separators=(',', ': '))
    with open(os.path.dirname(__file__) + "/../dist/capabilities.json", "wb+") as f:
        f.write(json_capabilities.encode('utf-8'))
        
    yml_capabilities = pyaml.dumps(json.loads(json_capabilities, object_pairs_hook=collections.OrderedDict), string_val_style='"')
    with open(os.path.dirname(__file__) + "/../dist/capabilities.yml", "wb+") as f:
        f.write(yml_capabilities)
