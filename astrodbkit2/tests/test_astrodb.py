# Testing for astrodb

import os
import json
import pytest
from astrodbkit2.astrodb import Database, create_database, Base
from astrodbkit2.schema_example import *

DB_PATH = 'astrodbkit2/tests/temp.db'
DB_DIR = 'astrodbkit2/tests/tempdata'


def test_nodatabase():
    connection_string = 'sqlite:///:memory:'
    with pytest.raises(RuntimeError, match='Create database'):
        db = Database(connection_string)


@pytest.fixture(scope="module")
def db():
    # Create a fresh temporary database and assert it exists
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    connection_string = 'sqlite:///' + DB_PATH
    create_database(connection_string)
    assert os.path.exists(DB_PATH)

    # Connect to the new database and confirm it has the Sources table
    db = Database(connection_string)
    assert db
    assert 'source' in [c.name for c in db.Sources.columns]

    return db


def test_add_data(db):
    # Load example data to the database
    publications_data = [{'name': 'Schm10',
                          'bibcode': '2010AJ....139.1808S',
                          'doi': '10.1088/0004-6256/139/5/1808',
                          'description': 'Colors and Kinematics of L Dwarfs From the Sloan Digital Sky Survey'},
                         {'name': 'Cutr12',
                          'bibcode': '2012yCat.2311....0C',
                          'doi': None,
                          'description': 'WISE All-Sky Data Release'}]
    db.Publications.insert().execute(publications_data)

    # Add telescope
    db.Telescopes.insert().execute([{'name': 'WISE'}])

    # Add source
    sources_data = [{'ra': 209.301675, 'dec': 14.477722,
                     'source': '2MASS J13571237+1428398',
                     'reference': 'Schm10',
                     'shortname': '1357+1428'}]
    db.Sources.insert().execute(sources_data)

    # Additional names
    names_data = [{'source': '2MASS J13571237+1428398',
                   'other_name': 'SDSS J135712.40+142839.8'},
                  {'source': '2MASS J13571237+1428398',
                   'other_name': '2MASS J13571237+1428398'},
                  ]
    db.Names.insert().execute(names_data)

    # Add Photometry
    phot_data = [{'source': '2MASS J13571237+1428398',
                  'band': 'WISE_W1',
                  'magnitude': 13.348,
                  'magnitude_error': 0.025,
                  'telescope': 'WISE',
                  'reference': 'Cutr12'
                  },
                 {'source': '2MASS J13571237+1428398',
                  'band': 'WISE_W2',
                  'magnitude': 12.990,
                  'magnitude_error': 0.028,
                  'telescope': 'WISE',
                  'reference': 'Cutr12'
                  }]
    db.Photometry.insert().execute(phot_data)


def test_query_data(db):
    # Perform some example queries and confirm the results
    assert db.query(db.Publications).count() == 2
    assert db.query(db.Sources).count() == 1
    assert db.query(db.Sources.c.source).limit(1).all()[0][0] == '2MASS J13571237+1428398'


def test_inventory(db):
    # Test the inventory method
    test_dict = {'Sources': [{'source': '2MASS J13571237+1428398',
                              'ra': 209.301675, 'dec': 14.477722,
                              'shortname': '1357+1428', 'reference': 'Schm10',
                              'comments': None}],
                 'Names': [{'other_name': '2MASS J13571237+1428398'},
                           {'other_name': 'SDSS J135712.40+142839.8'}],
                 'Photometry': [{'band': 'WISE_W1', 'ucd': None, 'magnitude': 13.348,
                                 'magnitude_error': 0.025, 'telescope': 'WISE', 'instrument': None,
                                 'epoch': None, 'comments': None, 'reference': 'Cutr12'},
                                {'band': 'WISE_W2', 'ucd': None, 'magnitude': 12.99,
                                 'magnitude_error': 0.028, 'telescope': 'WISE', 'instrument': None,
                                 'epoch': None, 'comments': None, 'reference': 'Cutr12'}]
                 }

    assert db.inventory('2MASS J13571237+1428398') == test_dict


def test_save_db(db):
    # Test saving the database to JSON files

    # Clear temporary directory first
    if not os.path.exists(DB_DIR):
        os.mkdir(DB_DIR)
    for file in os.listdir(DB_DIR):
        os.remove(os.path.join(DB_DIR, file))

    db.save_db(DB_DIR)

    # Check JSON data
    assert os.path.exists(os.path.join(DB_DIR, '2mass_J13571237+1428398_data.json'))
    assert os.path.exists(os.path.join(DB_DIR, 'Publications_data.json'))

    # Load source and confirm it is the same
    with open(os.path.join(DB_DIR, '2mass_J13571237+1428398_data.json'), 'r') as f:
        data = json.load(f)
    assert data == db.inventory('2MASS J13571237+1428398')


def test_load_database(db):
    # Test loading database from JSON files

    # First clear some of the tables
    db.Publications.delete().execute()
    db.Sources.delete().execute()

    # Reload the database and check DB contents
    db.load_database(DB_DIR)
    assert db.query(db.Publications).count() == 2
    assert db.query(db.Photometry).count() == 2
    assert db.query(db.Sources).count() == 1
    assert db.query(db.Sources.c.source).limit(1).all()[0][0] == '2MASS J13571237+1428398'

    # Clear temporary directory and files
    for file in os.listdir(DB_DIR):
        os.remove(os.path.join(DB_DIR, file))


def test_remove_database(db):
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)