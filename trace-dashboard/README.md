# trace dashboard

## how to run
``` bash
streamlit ./trace-dashboard.py
```

## NOTE
* リアルタイムにストリーム的な処理をするための試作品
* trace.jsonのデータ
  * B,E,Xのイベントは`ts`のタイムスタンプ順となっている想定のアルゴリズムである

## Issues
* グラフの操作がキーボードで容易にできない
* 棒グラフの高さが固定されているので、拡大時にx,y方向の両方がズームされ、スタックの重なりが見れない
