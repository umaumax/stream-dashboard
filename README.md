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

## TODO
* [ ] グラフの最終更新日時について、現状は絶対日時のみであるがN秒前更新という表示も追加できると良い(現状の仕組みだと常にpython側と通信して書き換える必要があり、これは本来はJSでやりたいが、裏技として、自作のchrome 拡張で実施する解決策もある)

## Ideas
* [ ] topでプロセスごとだけではなくスレッドごとが見えるようにする
  * [ ] kubernetesのpodごとの項目を追加する
* [ ] グラフの軸を特定のインクリメントなID or 時刻へ切り替えることができる機能

## Issues
* [ ] Downloadファイルボタンを押すとなぜかグラフが増える
* [ ] 普通のグラフと積み上げグラフではなぜか、左右の余白が異なる
