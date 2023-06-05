"""Process files exported from Samsung Health

Only supports oxygen saturation.

Author: William R. Zwicky <wrzwicky@pobox.com>

Created: 2 June 2023
"""

import copy
import csv
import json
import os
from datetime import datetime, timezone

## Samsung Health docs for OxygenSaturation:
## https://developer.samsung.com/health/android/data/api-reference/com/samsung/android/sdk/healthdata/HealthConstants.OxygenSaturation.html


def parseSamsungTime(timeStr):
  return datetime.strptime(timeStr, "%Y-%m-%d %H:%M:%S.%f")

def formatSamsungTime(datetimeobj):
  return datetime.strftime(datetimeobj, "%Y-%m-%d %H:%M:%S.%f")

def flot(s):
  """Convert parameter to float if truthy, else None.
  i.e. Zeros, empty strings, etc. all return None."""
  return float(s) if s else None

  
class HealthConstants:
  class OxygenSaturation:
    UUID = "com.samsung.health.oxygen_saturation.datauuid"
    DEVICE_UUID = "com.samsung.health.oxygen_saturation.deviceuuid"
    PACKAGE_NAME = "com.samsung.health.oxygen_saturation.pkg_name"
      #create_time = 'when a new data is inserted'
    CREATE_TIME = "com.samsung.health.oxygen_saturation.create_time"
      #update_time = 'when existing data is updated'
    UPDATE_TIME = "com.samsung.health.oxygen_saturation.update_time"
    START_TIME = "com.samsung.health.oxygen_saturation.start_time"
    END_TIME = "com.samsung.health.oxygen_saturation.end_time"
    TIME_OFFSET = "com.samsung.health.oxygen_saturation.time_offset"
    SPO2 = "com.samsung.health.oxygen_saturation.spo2"
    HEART_RATE = "com.samsung.health.oxygen_saturation.heart_rate"
    COMMENT = "com.samsung.health.oxygen_saturation.comment"
    CUSTOM = "com.samsung.health.oxygen_saturation.custom"
    # undocumented
    LOW_DURATION = "com.samsung.health.oxygen_saturation.low_duration"
    BINNING = "com.samsung.health.oxygen_saturation.binning"
    MAX_SPO2 = "com.samsung.health.oxygen_saturation.max"
    MIN_SPO2 = "com.samsung.health.oxygen_saturation.min"


class OxygenSaturation:
  def __init__(self, start, end, spo2min, spo2max, spo2, heart, low_duration):
    self.start = start
    self.end = end
    self.min = spo2min
    self.max = spo2max
    self.avg = spo2
    self.heart = heart
    self.low_duration = low_duration

  def __str__(self):
    return f"spo2 at {self.start} = {self.avg} @ {self.heart} BPM"

  def sufficient(self):
    """Return True if there's enough data to be worth saving."""
    return (self.min and self.max) or self.avg


class OxygenSaturationParser:

  def load(self, filename):
    """Load CSV file and all referenced 'binning' files. Returns list(OxygenSaturation)"""

    self.filename = filename
    oxygens = []
    
    with open(filename, newline='') as csvfile:
      # first line has file name plus 2 more unknown numbers
      linereader = csv.reader(csvfile)
      (self.title, unk2, unk3) = next(linereader)[0:3]
    
      # next line has column names
      dictreader = csv.DictReader(csvfile)
    
      for row in dictreader:
        oxygens += self.loadRow(row)

    oxygens.sort(key=lambda oxy: oxy.start)

    return oxygens


  def loadRow(self, rowdict):
    """Given one row from CSV file, will load all records from link JSON file if any.
    If JSON data found, CSV record is dropped. If none, CSV record is returned."""

    # Load CSV record as template
    base = self.parseRow(rowdict)

    jsonName = rowdict[HealthConstants.OxygenSaturation.BINNING]
    oxygens = []

    if jsonName:
      jsonPath = os.path.join(
        os.path.dirname(self.filename),
        "jsons", self.title, jsonName[0], jsonName)
      oxygens = self.loadJson(base, jsonPath)

    if oxygens:
      return oxygens
    else:
      return [base,]


  @classmethod
  def parseRow(cls, rowdict):
    """Convert one row from CSV file."""

    # time is actually GMT; time_offset is just for reference
    zone = timezone.utc #rowdict[cls.TIME_OFFSET]
    start = parseSamsungTime(rowdict[HealthConstants.OxygenSaturation.START_TIME]) \
          .replace(tzinfo=timezone.utc)
    end = parseSamsungTime(rowdict[HealthConstants.OxygenSaturation.END_TIME]) \
          .replace(tzinfo=timezone.utc)

    oxy = OxygenSaturation(
      start, end, 
      flot(rowdict[HealthConstants.OxygenSaturation.MIN_SPO2]),
      flot(rowdict[HealthConstants.OxygenSaturation.MAX_SPO2]),
      flot(rowdict[HealthConstants.OxygenSaturation.SPO2]),
      flot(rowdict[HealthConstants.OxygenSaturation.HEART_RATE]),
      flot(rowdict[HealthConstants.OxygenSaturation.LOW_DURATION]))
    
    return oxy


  @classmethod
  def loadJson(cls, base, filename):
    """Load and parse contents of JSON binning file, returning
    list of OxygenSaturation, each being a clone of 'base' with
    values replaced."""
    oxygens = []

    if os.path.exists(filename):
      with open(filename) as f:
        bins = json.load(f)

      for bin in bins:
        oxy2 = cls.parseJson(base, bin)
        if oxy2 and oxy2.sufficient():
          oxygens.append(oxy2)

    return oxygens


  @classmethod
  def parseJson(cls, base, record):
    """Clone given base, and replace data with values from JSON record."""

    # is list of {"spo2":0,"spo2_max":0,"spo2_min":0,"start_time":1662821111851,"end_time":1662821170851}

    start = datetime.fromtimestamp(record['start_time']/1000) \
          .replace(tzinfo=timezone.utc)
    end = datetime.fromtimestamp(record['end_time']/1000) \
          .replace(tzinfo=timezone.utc)
    
    oxy2 = copy.copy(base)
    oxy2.start = start
    oxy2.end = end

    # if average defined, save it
    if record['spo2']:
      oxy2.avg = flot(record['spo2'])

    # if min and max defined, save them
    if record['spo2_min'] and record['spo2_max']:
      oxy2.min = flot(record['spo2_min'])
      oxy2.max = flot(record['spo2_max'])
      # spo2 field is always 0 in my jsons
      if not oxy2.avg:
        oxy2.avg = (oxy2.min + oxy2.max) / 2
    else:
      oxy2.min = None
      oxy2.max = None

    return oxy2
