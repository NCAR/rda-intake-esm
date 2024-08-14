#!/usr/bin/env python
import sys
import os
import argparse
import re
import pdb

import xarray
import pandas as pd
import intake_esm
import ecgtools



NO_DATA_STR = ""

def get_parser():
    description = "CLI to generate intake-esm cataloges."
    parser = argparse.ArgumentParser(
            prog='create_catalog',
            description=description,
            formatter_class=argparse.RawDescriptionHelpFormatter)

    # Arguments that are always allowed
    parser.add_argument('directories',
            nargs='+',
            metavar='<directory>',
            help="Directory or directories to scan.")
    parser.add_argument('--out', '-o',
            type=str,
            required=False,
            metavar='<directory>',
            default='./',
            help="Directory to ouput json and csv.")
    parser.add_argument('--catalog_name', '-n',
            type=str,
            required=False,
            metavar='<name>',
            default='catalog',
            help="Name of catalog")
    parser.add_argument('--description',
            type=str,
            required=False,
            metavar='<description>',
            default='N/A',
            help="Description of catalog")
    parser.add_argument('--exclude', '-e',
            nargs='*',
            required=False,
            metavar='<glob>',
            help="Exclude glob")
    parser.add_argument('--depth', '-d',
            type=int,
            nargs='*',
            required=False,
            metavar='<value>',
            default=0,
            help="depth to search")
    parser.add_argument('--ignore_vars', '-i',
            type=str,
            nargs='*',
            required=False,
            metavar='<var name>',
            default=[],
            help="Optionally ignore specific variables e.g. utc_date")
    parser.add_argument('--var_metadata', '-vm',
            type=str,
            required=False,
            metavar='<json string/filename>',
            default='{}',
            help="Additional variable level metadata to extract.")
    parser.add_argument('--global_metadata', '-gm',
            type=str,
            required=False,
            metavar='<json string/filename>',
            default='{}',
            help="Additional global level metadata to extract.")

    return parser

def get_engine(file_path):
    """Gets xarray engine based on file."""
    #TODO: what if kerchunk reference?
    if re.match('.*\.nc$', file_path):
        return 'netcdf4'
    if re.match('.*\.grib$', file_path) or re.match('.*\.grb$', file_path):
        return 'cfgrib'
    if re.match('.*\.zarr$', file_path):
        return 'zarr'

def file_parser(file_path, ignore_vars=[], var_attrs=[]):
    """File parser used in Builder object to extract column values.

    Args:
        file_path (str, Path): path to data_file
        ignore_vars (list[str]): Variable names to ignore. e.g. 'utc_time'

    Returns:
        dict: Keys are column names and values specific to file.
    """
    engine = get_engine(file_path)
    rows = []
    with xarray.open_dataset(file_path, engine=engine) as ds:
        for var_name in ds.data_vars:
            row = {'path':file_path, 'variable':var_name}
            var = ds[var_name]
            row.update(get_var_attrs(var))
            rows.append(row)
    return rows

def get_default_var_metadata():
    # Default metadata to check in a variable.
    # The key is the attr name. The value is default value.
    default_var_attrs = {
            'long_name' : {'':''},
            'short_name' : {'':''},
            }
    return default_var_attrs

def get_var_attrs(var):
    """Gets relevant metadata from xarray DataArray-like object.

    Args:
        var (xarray.core.dataarray.DataArray): Variable to pull attributes.

    Returns:
        dict: Contains variable level metadata
    """
    var_attrs = {}
    var_attrs['short_name'] = var.attrs.get('short_name', var.name)
    var_attrs['long_name'] = var.attrs.get('long_name', NO_DATA_STR)
    var_attrs['units'] = var.attrs.get('units', NO_DATA_STR)
    return var_attrs



def main(args_list):
    """Use command line-like arguments to execute

    Args:
        args_list (unpacked list): list of args as they would be passed to command line.

    Returns:
        (dict, generally) : result of argument call.
    """
    parser = get_parser()
    if len(args_list) == 0:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args(args_list)
    print(args)
    args_dict = vars(args)
    create_catalog(**args_dict)


def create_catalog(directories, out='./', depth=0, exclude='',
                   catalog_name='catalog', description='',  **kwargs):
    print(kwargs)
    b = ecgtools.Builder(paths=directories,
                         depth=depth,
                         exclude_patterns=exclude)
    pdb.set_trace()
    b.build(parsing_func=file_parser)

    # extract dicts and combine
    new_df = pd.DataFrame(columns=b.df[0][0].keys())
    dict_list = []
    for i,d in b.df.iterrows():
        for j in d:
            dict_list.append(j)
    pdb.set_trace()
    b.df = new_df.from_records(dict_list)

    b.save(
    name=catalog_name,
    path_column_name='path',
    variable_column_name='variable',
    data_format='netcdf',
    groupby_attrs=[
        'variable',
        'short_name'
    ],
    aggregations=[
        {'type': 'union', 'attribute_name': 'variable'},
        {
            'type': 'join_existing',
            'attribute_name': 'time_range',
            'options': {'dim': 'time', 'coords': 'minimal', 'compat': 'override'},
        },
    ],
    description = description,
    directory = out
    )


if __name__ == '__main__':
    main(sys.argv[1:])

