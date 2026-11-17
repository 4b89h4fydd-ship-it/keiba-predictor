# horse-profiles

馬詳細パネルの血統・馬主・生産者表示が読む日付別JSONの置き場。
形式と収集方法は `docs/horse_profiles_collection.md` を参照。

- ファイル名: `<YYYY-MM-DD>.json`
- `build_static.py` が日付パターンに一致するJSONだけを dist へコピーする。
- ファイルが無い日は、クライアントは該当項目を「収集中」と表示する。
