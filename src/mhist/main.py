import argparse
import json
import sys
from datetime import datetime
from pathlib import Path, PurePath
from platform import node as get_hostname

import jinja2
from fuzzywuzzy import fuzz


class colors:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'


def process_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title='Actions', dest='subparser')

    record_parser = subparsers.add_parser('record', help='Record entry.')

    record_required_exclusive_parent = record_parser.add_argument_group('Required either of')
    record_required_exclusive = record_required_exclusive_parent.add_mutually_exclusive_group(required=True)

    record_required_exclusive.add_argument(
        '--from-string', action='store', type=str,
        help="Take record from string passed as argument."
    )

    record_required_exclusive.add_argument(
        '--from-stdin', action='store_true',
        help="Read items to record from stdin, separated by new line."
    )

    query_parser = subparsers.add_parser('query', help='Query the saved history.')

    query_parser.add_argument(
        '--limit', action='store', type=int, default='10',
        help="Print at most N matching/latest records. Set to 0 to print all. Default is 10."
    )

    query_parser.add_argument(
        '--fuzzy-ratio', action='store', type=int, default='63',
        help="When --fuzzy is in use, accept entries that reach >= N partial ratio. Default is 63."
    )

    query_required_exclusive_parent = query_parser.add_argument_group('Required either of')
    query_required_exclusive = query_required_exclusive_parent.add_mutually_exclusive_group(required=True)

    query_required_exclusive.add_argument(
        '--fuzzy', action='store', type=str,
        help="Case insensitive fuzzy search, processes list from newest to oldest entry."
    )

    query_required_exclusive.add_argument(
        '--with-words', action='store', type=str,
        help="Split passed string by spaces, check if all of the words are present in entry, in any order and case insensitive."
    )

    query_required_exclusive.add_argument(
        '--last', action='store_true',
        help="List last entries"
    )

    deploy_parser = subparsers.add_parser('deploy', help='Control integration with mpv')
    deploy_required_exclusive_parent = deploy_parser.add_argument_group('Required either of')
    deploy_required_exclusive = deploy_required_exclusive_parent.add_mutually_exclusive_group(required=True)

    deploy_required_exclusive.add_argument(
        '--enable', action='store_true',
        help="Create ~/.mpv/scripts/mhist.lua with global mhist or local path to mhist script."
    )

    deploy_required_exclusive.add_argument(
        '--disable', action='store_true',
        help="Remove ~/.mpv/scripts/mhist.lua."
    )

    args, extra_args = parser.parse_known_args()
    if extra_args:
        if extra_args[0] != '--':
            parser.error(f"Custom arguments are to be passed after '--'.")
        extra_args.remove('--')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    return args, extra_args


def main_record(config, args):
    if args.from_stdin:
        records = sys.stdin.read().splitlines()
    elif args.from_string:
        records = [args.from_string]
    else:
        raise

    date_now = datetime.now()

    data_dir = Path().joinpath(
        config['mhist_root'], 'data', 'per-host', get_hostname()
    )

    if not data_dir.is_dir():
        data_dir.mkdir(parents=True)

    records_file = Path().joinpath(
        data_dir,
        "{date_now}".format(date_now=date_now.strftime("%Y-%m"))
    )

    with records_file.open(mode="a") as f:
        for record in records:
            file_handler = Path(record)

            # If it exists, assume it's local file, if not, assume it's remote link.
            # In case of local, record parent directory+filename.
            if file_handler.exists():
                record_type = 'local'
                record_item = '/'.join(str(file_handler.resolve()).split('/')[-2:])
            else:
                record_type = 'remote'
                record_item = record

            f.write(
                "{timestamp} {record_type} {record_item}\n".format(
                    timestamp=date_now.timestamp(),
                    record_type=record_type,
                    record_item=record_item
                )
            )


def print_record(record):
    record_timestamp, record_type, record_item = record.split(' ', 2)

    record_date = datetime.fromtimestamp(float(record_timestamp)).strftime("%Y-%m-%d %H:%M:%S")

    prefix = "[{record_date}] ".format(
        record_date=record_date,
    )

    if record_type == 'local' and '/' in record_item:
        parent, basename = record_item.rsplit('/')

        output_string = "{prefix}{parent}/{bold}{color}{basename}{reset}".format(
            prefix=prefix,
            bold=colors.BOLD,
            color=colors.YELLOW,
            parent=parent,
            basename=basename,
            reset=colors.RESET
        )
    else:
        # Records of remote streams and old imported data have no parent directories.
        output_string = "{prefix}{bold}{color}{record_item}{reset}".format(
            prefix=prefix,
            bold=colors.BOLD,
            color=colors.YELLOW,
            record_item=record_item,
            reset=colors.RESET
        )

    print(output_string)


def slice_record(record):
    record_time, record_type, record_item = record.split(' ', 2)

    return {
        'time': record_time,
        'type': record_type,
        'item': record_item
    }


def main_query(config, args):
    records = []

    # Load preprocessed initial records, from merge-and-truncate.
    initial_records = Path().joinpath(
        config['mhist_root'],
        'data',
        'common',
        'initial_records'
    )

    if initial_records.exists():
        records.extend(initial_records.read_text().splitlines())

    per_host_path = PurePath().joinpath(
        config['mhist_root'],
        'data',
        'per-host'
    )

    per_host_records = []
    for per_host_record_file in Path(per_host_path).glob('*/*'):
        per_host_records.extend(Path(per_host_record_file).read_text().splitlines())

    per_host_records.sort(key=lambda x: x.split(' ', 1)[0])

    records.extend(per_host_records)

    if args.last:
        if args.limit != 0:
            # Limit to only N last records.
            records = records[-args.limit:]

        for idx in range(len(records) - 1, -1, -1):
            print_record(records[idx])
    else:
        matched = 0

        if args.fuzzy:
            for idx in range(len(records) - 1, -1, -1):
                if args.limit > 0 and matched == args.limit:
                    break

                record = records[idx]
                entry = record.split(' ', 2)[2]
                if fuzz.partial_ratio(args.fuzzy.lower(), entry.lower()) >= args.fuzzy_ratio:
                    matched += 1
                    print_record(record)

        elif args.with_words:
            for idx in range(len(records) - 1, -1, -1):
                if args.limit > 0 and matched == args.limit:
                    break

                record = records[idx]
                entry = record.split(' ', 2)[2].lower()

                words = args.with_words.lower().split(' ')

                if all(word in entry for word in words):
                    matched += 1
                    print_record(record)


def main_dispatcher(config, args, extra_args):
    if args.subparser == 'record':
        main_record(config, args)
    elif args.subparser == 'query':
        main_query(config, args)
    elif args.subparser == 'deploy':
        main_deploy(config, args)
    else:
        raise


def main_deploy(config, args):
    if args.enable:
        # If installed via setup.py, will use `mhist` from $PATH.
        # otherwise hardcode fullpath for entrypoint script.
        if vars(sys.modules[__name__])['__package__'] == 'src.mhist':
            mhist_script = sys.argv[0]
        else:
            mhist_script = 'mhist'

        mhist_lua_template = Path().joinpath(Path(__file__).parent, 'mhist.lua.j2').read_text()

        mhist_lua = jinja2.Environment(
            loader=jinja2.BaseLoader(), keep_trailing_newline=True
        ).from_string(mhist_lua_template).render({'mhist_script': mhist_script})

        mpv_scripts_dir = Path().joinpath(Path().home(), '.mpv', 'scripts')

        if not mpv_scripts_dir.exists():
            mpv_scripts_dir.mkdir(parents=True)

        Path().joinpath(mpv_scripts_dir, 'mhist.lua').write_text(mhist_lua)

    elif args.disable:
        Path().joinpath(Path().home(), '.mpv', 'scripts', 'mhist.lua').unlink()


def get_config():
    # Defaults
    config = {
        'mhist_root': str(PurePath().joinpath(Path().home(), '.config', 'mhist'))
    }

    # Override with ~/.config/mhist/config.json
    user_config = Path().joinpath(Path().home(), '.config', 'mhist', 'config.json')
    if user_config.exists():
        config.update(
            json.loads(user_config.read_text())
        )

    return config


def main():
    config = get_config()

    args, extra_args = process_args()
    main_dispatcher(config, args, extra_args)
