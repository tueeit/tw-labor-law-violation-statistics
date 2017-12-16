- statistics.py: 統計主程式
- violation-record_utf8.csv: 由`求職小幫手`取得的違法紀錄。[原始來源](https://gist.github.com/ronnywang/860c6f9a9acac7f4e561e1611d700bd2/raw/18c4c6808df4143c0b378cb269021d2d919b04cd/all.csv)
- comany-info.json: 公司資料快取資料，執行統計程式時若沒有這個檔案，會依違法紀錄向[g0v](http://company.g0v.ronny.tw/)查詢，並建立快取。
  在沒有快取的狀況下，統計程式需執行約一小時。
- violation-record-extended_utf8.csv: 違法紀錄，並加上違法公司的資本額資料。
- violation-statistics_utf8.csv: 統計結果。

執行方式: `python3 statistics.py`
