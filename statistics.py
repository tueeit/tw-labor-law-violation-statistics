#!python3
import re
import csv
import json
import pprint
import urllib.request
import urllib.parse

DEBUG = False
RUN_SIZE = -1

# currently from https://gist.github.com/ronnywang/860c6f9a9acac7f4e561e1611d700bd2/raw/18c4c6808df4143c0b378cb269021d2d919b04cd/all.csv
VIOLATION_RECORD_FILENAME = "violation-record_utf8.csv"
VIOLATION_RECORD_EXTENDED_FILENAME = "violation-record-extended_utf8.csv"
VIOLATION_STATISTICS_FILENAME = "violation-statistics_utf8.csv"
COMPANY_INFO_CACHE_FILENAME = "comany-info.json"

PAID_IN_CAPITAL_FIELD_NAME = "實收資本額(元)"
CAPITAL_FIELD_NAME = "資本額(元)"
# SME for Small and Medium-size Enterprise, and LE for Large Enterprise
ENTERPRISE_CATEGORY = ['中小企業', '大型企業', '查無登記']
SME_CAPTICAL_LIMIT = 80000000

pp = pprint.PrettyPrinter(indent=4)
def debug_dump(step, title, data):
    if not DEBUG:
        return
    print("### Step %d, %s: " % (step, title))
    pp.pprint(data)

current_step = 0

current_step = current_step + 1
print("# Step %d: Import raw data" % current_step)
violation_records = []
field_names = None
with open(VIOLATION_RECORD_FILENAME, newline='', encoding='utf-8') as violation_record_file:
    violation_record_reader = csv.DictReader(violation_record_file,
                                             delimiter=',',
                                             quotechar='"')
    field_names = violation_record_reader.fieldnames
    for violation_record in violation_record_reader:
        violation_records.append(violation_record)

if RUN_SIZE is None or RUN_SIZE <= 0:
    RUN_SIZE = len(violation_records)

debug_dump(current_step, "Field names", field_names)
debug_dump(current_step, "Violation Records", violation_records[0:RUN_SIZE])

current_step = current_step + 1
print("# Step %d: Load company info cache if possible" % current_step)
try:
    with open(COMPANY_INFO_CACHE_FILENAME, encoding='utf-8') as company_info_file:
        company_info_cache = json.load(company_info_file)
except:
    company_info_cache = {}

debug_dump(current_step, "Company Info Cache", company_info_cache)

current_step = current_step + 1
print("# Step %d: Look and fill '實收資本額' into violation record and build company info cache" % current_step)

for index, violation_record in enumerate(violation_records[0:RUN_SIZE]):
    company_name = violation_record['事業單位']

    company_name_match = re.match(r'.*[(（]即(.*)[)）]', company_name)
    if company_name_match is not None:
        company_name = company_name_match.group(1)

    print("Look Up Company Info: %d/%d" % (index + 1, RUN_SIZE))
    try:
        company_info = company_info_cache[company_name]
        debug_dump(current_step, "Get Company Info From Cache", company_info)
    except:
        try:
            response = urllib.request.urlopen("http://company.g0v.ronny.tw/api/search?q=" + urllib.parse.quote(company_name))
            response_data = json.loads(response.read().decode('utf-8'))
            if response_data['found'] == 0:
                raise Exception

            company_data = None
            for company in response_data['data']:
                if ("公司名稱" in company.keys() and company["公司名稱"] == company_name) or \
                    ("商業名稱" in company.keys() and company["商業名稱"] == company_name):
                    company_data = company
                    break

            if company_data is None:
                raise Exception

            paid_in_capital = None
            capital = None

            if PAID_IN_CAPITAL_FIELD_NAME in company_data.keys():
                paid_in_capital = int(company_data[PAID_IN_CAPITAL_FIELD_NAME].replace(',', ''))

            if "資本總額(元)" in company_data.keys():
                capital =int(company_data["資本總額(元)"].replace(',', ''))
            elif "資本額(元)" in company_data.keys():
                capital =int(company_data["資本額(元)"].replace(',', ''))
            elif "財政部" in company_data.keys():
                if "資本額" in company_data["財政部"].keys():
                    capital =int(company_data["財政部"]["資本額"].replace(',', ''))

            company_info = {
                PAID_IN_CAPITAL_FIELD_NAME: paid_in_capital,
                CAPITAL_FIELD_NAME: capital
            }
        except:
            company_info = {
                PAID_IN_CAPITAL_FIELD_NAME: None,
                CAPITAL_FIELD_NAME: None
            }
        finally:
            company_info_cache[company_name] = company_info
            debug_dump(current_step, "Query Company Info From Remote", company_info)

    try:
        violation_record[PAID_IN_CAPITAL_FIELD_NAME] = company_info[PAID_IN_CAPITAL_FIELD_NAME]
        violation_record[CAPITAL_FIELD_NAME] = company_info[CAPITAL_FIELD_NAME]
    except:
        violation_record[PAID_IN_CAPITAL_FIELD_NAME] = None
        violation_record[CAPITAL_FIELD_NAME] = None

current_step = current_step + 1
print("# Step %d: Save violation records containing extra information" % current_step)

with open(VIOLATION_RECORD_EXTENDED_FILENAME, mode='w', newline='',
          encoding='utf-8') as violation_record_file:
    violation_record_writer = csv.DictWriter(
        violation_record_file,
        fieldnames=field_names + [PAID_IN_CAPITAL_FIELD_NAME, CAPITAL_FIELD_NAME]
    )

    violation_record_writer.writeheader()
    for violation_record in violation_records[0:RUN_SIZE]:
        violation_record_writer.writerow(violation_record)

debug_dump(current_step, "Violation Records", violation_records[0:RUN_SIZE])

current_step = current_step + 1
print("# Step %d: Save company info cache" % current_step)

with open(COMPANY_INFO_CACHE_FILENAME, mode='w', encoding='utf-8') as company_info_file:
    json.dump(company_info_cache, company_info_file)

debug_dump(current_step, "Dump Company Info Cache", company_info_cache)

print("# Step %d: Do Violation Statistics" % current_step)
current_step = current_step + 1

violation_count_by_law = {category: {} for category in ENTERPRISE_CATEGORY}
violation_total = {category: 0 for category in ENTERPRISE_CATEGORY}

for index, violation_record in enumerate(violation_records[0:RUN_SIZE]):
    company_paid_in_capital = violation_record[PAID_IN_CAPITAL_FIELD_NAME]
    company_capital = violation_record[CAPITAL_FIELD_NAME]
    violation_law = violation_record['法條種類'] + violation_record['法條']

    print("Generate Statistics: %d/%d " % (index + 1, RUN_SIZE))

    if company_paid_in_capital is None and company_capital is None:
        category = '查無登記'
    elif (company_paid_in_capital is not None and company_paid_in_capital <= SME_CAPTICAL_LIMIT) or \
        (company_capital is not None and company_capital <= SME_CAPTICAL_LIMIT):
        category = '中小企業'
    else:
        category = '大型企業'

    violation_total[category] = violation_total[category] + 1
    try:
        violation_count_by_law[category][violation_law] = violation_count_by_law[category][violation_law] + 1
    except:
        violation_count_by_law[category][violation_law] = 1

for category in ENTERPRISE_CATEGORY:
    debug_dump(current_step, "Violation by Law of " + category, violation_count_by_law[category])
    debug_dump(current_step, "Total Violation of " + category, violation_total[category])

current_step = current_step + 1
print("# Step %d: Save Violation Statistics" % current_step)

with open(VIOLATION_STATISTICS_FILENAME, mode='w', newline='',
          encoding='utf-8') as violation_statistics_file:
    violation_statistics_writer = csv.writer(violation_statistics_file,
                                             delimiter=',',
                                             quotechar='"')

    violation_statistics_writer.writerow(['企業規模', '違反法條', '違法次數', '違法比例'])
    for category in ENTERPRISE_CATEGORY:
        for violation_law in violation_count_by_law[category]:
            violation_count = violation_count_by_law[category][violation_law]
            violation_statistics_writer.writerow([
                category,
                violation_law,
                violation_count,
                round(violation_count * 100 / violation_total[category], 2)
            ])
