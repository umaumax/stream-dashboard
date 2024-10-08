# stream-dashboard

## how to run top.py
``` bash
top -b -d 1 -n10 > top-b-n-10-d-1.log

./top.py -in top-b-n-10-d-1.log -o top.jsonl
```

## how to run dashboard
``` bash
streamlit run ./dashboard.py
```

### how to login
`testuser` / `PassW0rd`

## how to run tests
``` bash
pytest ./test.py
```

## TODO
* [ ] グラフの最終更新日時について、現状は絶対日時のみであるがN秒前更新という表示も追加できると良い(現状の仕組みだと常にpython側と通信して書き換える必要があり、これは本来はJSでやりたいが、裏技として、自作のchrome 拡張で実施する解決策もある)

## Ideas
* [ ] バックグラウンドでコマンドを実行して、グラフ用のプロットデータを作成する仕組みを実装する
  * [umaumax/flock_wrapper]( https://github.com/umaumax/flock_wrapper/tree/main/ )を利用すると良い
* [ ] topでプロセスごとだけではなくスレッドごとが見えるようにする
  * [ ] kubernetesのpodごとの項目を追加する
* [ ] グラフの軸を特定のインクリメントなID or 時刻へ切り替えることができる機能
* [ ] グラフを個別のページに表示する機能

## Issues
* [ ] Downloadファイルボタンを押すとなぜかグラフが増える
* [ ] 普通のグラフと積み上げグラフではなぜか、左右の余白が異なる

## グラフデータ定義ファイル仕様
ファイル名: `*.decl.json`

* `data{[]}`/`data[{}]`: データをそのまま埋め込む
  * `pandas`がサポートする形式であれば次のどちらでもよい
``` json
"data": {
  "sepal_length": [0.1, 0.4, 1.2, 2.1, -1.9, 1],
  "sepal_width": [1, 2, 4, 8, 10, 3],
  "species": ["a", "b", "a", "c", "b", "b"]
},
"data": [
  {
    "x": [1, 2, 3, 4, 5],
    "y": [2, 13, 5, 7, 11],
    "z": [1, 2, 5, 6, 7],
    "mode": "markers",
    "name": "Series 1"
  },
  {
    "x": [2, 3, 4, 5, 6],
    "y": [3, 4, 36, 8, 12],
    "z": [10, 12, 15, 16, 17],
    "mode": "lines",
    "name": "Series 2"
  }
],
```

* `ref-data{}`: データが保存されている定義ファイルからの相対パス or 絶対パスを指定する
  * ファイルは初めから存在しておらず、後から生成されたり、新規に上書き、随時追加書き込みが実施されても問題ない
  * サポートされているファイル形式は`json`,`jsonl`
    * `csv`はサポート予定

* `funcs[]`: データに対する処理を記述する
  * 上から順番に処理される
  * `name`で指定した処理に対して、`args`の引数を適用する
