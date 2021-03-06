#!/usr/bin/env python3
'''diet is a minimalistic calorie tracking program. It aims to offer the
capability of remembering the total calorie consumption per day.
'''

import argparse
import collections
import datetime

import database_io

Food = collections.namedtuple('Food', ['calories', 'description'])

def search_case_insensitive_food(food, food_db, include_len=False):
    '''search food_db for keys that contain 'food'.
    If include_len is True, return a tuple with the second entry being the
    length of the longest match.
    '''
    search_lower = args.food.lower()
    def check_for_match(query):
        if search_lower in query.lower(): return True
        return False
    results = []
    max_name_len = 0
    for food in food_db.keys():
        if not check_for_match(food): continue
        results.append(food)
        if len(food) > max_name_len:
            max_name_len = len(food)
    if include_len:
        return (results, max_name_len)
    return results

def print_bar(total, target, display_area=80):
    '''print a progress bar that shows how many calories have been eaten.
    If the total is larger than the target, the border will be drawn shorter
    to maintain all proportions and the overall width of the bar.
    '''
    if total < target:
        barwidth = display_area
        fillwidth = round(display_area*total/target)
    else:
        barwidth = round(target/total*display_area)
        fillwidth = display_area
    print(' ' + '-'*(barwidth-2) + ' ')
    bar = '='*fillwidth + ' '*(display_area-fillwidth)
    print('|' + bar[:barwidth-2] + '|' + bar[barwidth:])
    print(' ' + '-'*(barwidth-2) + ' ')

def print_status(total, date_offset, day, added=None):
    dayformat = {
        0: 'today',
        1: 'yesterday',
        }
    if added is None:
        format_string = 'Daily total for {day}: {total}'
    else:
        format_string = ('Added {added:.0f} calories for {day}. '
            + 'Daily total: {total:.0f}')
    message = format_string.format(
        added=added,
        day=dayformat.get(date_offset, day.strftime('%A, %Y-%m-%d')),
        total=total,
        )
    print(message)
    try:
        user_db = database_io.get_db('user')
    except FileNotFoundError:
        user_db = dict()
    if 'target' in user_db:
        target = user_db['target']
        message = '{:.0%} of targeted {:.0f} calories'.format(
            total / target,
            target,
            )
        print(message)
        print_bar(total, target)

def status(args):
    '''print the user's calories.
    '''
    calorie_db = database_io.get_db('calorie')
    day = datetime.date.today() - datetime.timedelta(days=args.yesterday)
    print_status(
        total=calorie_db[day],
        date_offset=args.yesterday,
        day=day,
        )

def eat(args):
    '''eat is the method that executes either a lookup for the calories of a
    named piece of food from the food database or uses the calories provided
    by the user and adds them (multiplied by the number of portions) to the
    calorie database for the right day.

    args is an argparse Namespace object.
    '''
    # if we have to look the calories up...
    if args.food:
        food_db = database_io.get_db('food')
        # food_db contains dict with Food(namedtuple) values
        try:
            calories_base = food_db[args.food].calories
        except KeyError:
            results = search_case_insensitive_food(
                args.food,
                food_db,
                include_len=False
                )
            if len(results) == 1:
                message = (
                    "No match for '{}', but found '{}'. Using this instead."
                        .format(args.food, results[0]))
                print(message)
                calories_base = food_db[results[0]].calories
            else:
                print("Could not find '{}' in the food database."
                    .format(args.food))
                return
    # ...otherwise, we take the user-provided value
    else:
        calories_base = args.calories
    try:
        calorie_db = database_io.get_db('calorie')
    except FileNotFoundError:
        calorie_db = collections.Counter()
    day = datetime.date.today() - datetime.timedelta(days=args.yesterday)
    # calories_base times portion size
    # product will be added to the daily total
    calories_to_add = calories_base * args.number
    calorie_db[day] += calories_to_add
    database_io.ensure_appdata_existence()
    database_io.put_db('calorie', calorie_db)
    # print status _after_ file is written
    print_status(
        total=calorie_db[day],
        date_offset=args.yesterday,
        day=day,
        added=calories_to_add,
        )

def remember(args):
    '''remember is the method that stores the calories and the description in
    form of a Food object in the food database.

    args is an argparse Namespace object.
    '''
    food_data = Food(calories=args.calories, description=args.description)
    try:
        food_db = database_io.get_db('food')
    except FileNotFoundError:
        database_io.ensure_appdata_existence()
        food_db = dict()
    food_db[args.food] = food_data
    database_io.put_db('food', food_db)

def forget(args):
    '''forget removes a given item from the food database.
    '''
    food_db = database_io.get_db('food')
    del food_db[args.food]
    database_io.put_db('food', food_db)

def lookup(args):
    '''lookup is the method that searches the food database for a food with the
    provided name and outputs their calories and descriptions.

    args is an argparse Namespace object.
    '''
    food_db = database_io.get_db('food')
    # the length of the longest match, used for formatting
    if args.exact:
        if args.food in food_db:
            results = [args.food]
            max_name_len = len(args.food)
    else:
        (results, max_name_len) = search_case_insensitive_food(
            args.food,
            food_db,
            include_len=True,
            )
    headerformat = '{{0:<{m}}}  {{1:>5}}  {{2}}'.format(m=max_name_len)
    tableformat = '{{0:<{m}}}  {{1:>5.0f}}  {{2}}'.format(m=max_name_len)
    if results:
        if len(results) == 1:
            print('Found one match:\n')
        else:
            print('Found {} matches:\n'.format(len(results)))
        for food in sorted(results):
            food_data = food_db[food]
            print(tableformat.format(food,
                food_data.calories, food_data.description))
    else:
        print('Found no match.')

def user_set(args):
    '''set values of personal variables and store into user database.
    '''
    if not args.target is None:
        try:
            user_db = database_io.get_db('user')
        except FileNotFoundError:
            database_io.ensure_appdata_existence()
            user_db = dict()
        user_db['target'] = args.target
        # don't let target produce zero division
        if args.target == 0:
            del user_db['target']
        database_io.put_db('user', user_db)

# This dictionary associates the methods with the commands from the argparse
# Namespace object
command_dispatcher = {
    'eat': eat,
    'remember': remember,
    'forget': forget,
    'lookup': lookup,
    'set': user_set,
    'status': status,
    }

parser = argparse.ArgumentParser(
    description='''diet is a minimalistic calorie tracking program.
        It aims to offer the capabilty of remembering the total calorie
        consumption per day.''',
    )
subparsers = parser.add_subparsers(
    title='available commands',
    dest='command',
    )

eat_parser = subparsers.add_parser(
    'eat',
    description='''This command either looks up a given food in the database
        and adds it's calories to the daily total or adds the directly given
        amount of calories.''',
    usage='%(prog)s [-h] [-y] [-n NUM] {[-c CAL] | FOOD}',
    help='add calories to the daily calorie count',
    )

# either enter number of calories or food name:
choice_group = eat_parser.add_mutually_exclusive_group(required=True)
choice_group.add_argument(
    'food',
    nargs='?',
    metavar='FOOD',
    help='the name of the food to add',
    )
choice_group.add_argument(
    '-c', '--calories',
    metavar='CAL',
    type=float,
    help='the number of calories per portion to add, instead of FOOD',
    )

# needs to consider when calorie amount is given per 100g
# entering weight in grams might be preferred.
eat_parser.add_argument(
    '-n', '--number',
    metavar='NUM',
    type=float,
    default=1,
    help='the number of times a calorie amount is added',
    )
eat_parser.add_argument(
    '-y', '--yesterday',
    action='count',
    default=0,
    help='''add the calories to yesterday's instead of today's count.
        Can be repeated to address earlier days.''',
    )

remember_parser = subparsers.add_parser(
    'remember',
    description='''This command stores the given food with it's calories in the
        database to be later on accessed via the eat command.''',
    help='remember the calories of an item of food',
    )
remember_parser.add_argument(
    'food',
    metavar='FOOD',
    help='the name of the food to remember',
    )
remember_parser.add_argument(
    'calories',
    metavar='CAL',
    type=float,
    help='the number of calories of that item of food',
    )
remember_parser.add_argument(
    'description',
    metavar='DESC',
    nargs='?',
    help='an optional description',
    default='',
    )

status_parser = subparsers.add_parser(
    'status',
    description='''This command shows you how many calories you've consumed
        already.''',
    help="show how many calories you've consumed",
    )
status_parser.add_argument(
    '-y', '--yesterday',
    action='count',
    default=0,
    help='''show calories for yesterday instead of today.
        Can be repeated to address earlier days.''',
    )

forget_parser = subparsers.add_parser(
    'forget',
    description='''This command lets you remove a piece of food from the food
        database.''',
    help='remove food from database',
    )
forget_parser.add_argument(
    'food',
    metavar='FOOD',
    help='the name of the food to remove',
    )

lookup_parser = subparsers.add_parser(
    'lookup',
    description='''This command let's you look up a piece of food in the
        database and report it's calories and the associated description.''',
    help='look up piece of food in the database',
    )
lookup_parser.add_argument(
    '-e', '--exact',
    action='store_true',
    help='only look for one result that matches the search string exactly',
    )
lookup_parser.add_argument(
    'food',
    metavar='STRING',
    help='the string to look for',
    )

set_parser = subparsers.add_parser(
    'set',
    description='''This command let's you store values for personal parameters.
        They will be considered in the status message to be printed after
        invocation of the `eat` command.''',
    help='set personal parameters of which later status messages depend upon',
    )
set_parser.add_argument(
    'target',
    metavar='TARGET',
    type=float,
    help='the targeted total amount of calories per day',
    )

if __name__ == '__main__':
    args = parser.parse_args()
    command_dispatcher[args.command](args)

