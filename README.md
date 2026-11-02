# create_jarvis

Claude を頭脳にした、自分専用の「ジャービス」風AIアシスタントです。Windows PC で動かすことを前提にしています。

## ロードマップ

1. **土台づくり**（このバージョン）: ターミナルで会話できるアシスタント。Claude API とツール呼び出しの仕組み、Web検索での調べ物、危険な操作の確認機能。
2. **PC操作と調べ物の強化**: アプリ起動、ファイル検索・整理、コードの読み書きなどのツールを追加。
3. **音声で話す**: 「ジャービス」の呼びかけで起動し、日本語で聞き取り・読み上げ。
4. **スマートホーム**: 機器を購入後に連携（SwitchBot など API のある製品を想定）。

## セットアップ（Windows）

Python 3.10 以上が必要です。PowerShell で次を実行します。

```powershell
git clone https://github.com/kawajikohei/create_jarvis.git
cd create_jarvis
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
notepad .env   # ANTHROPIC_API_KEY を書き込む
```

`Activate.ps1` が実行ポリシーで止められたら、一度だけ `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` を実行してください。

## 使い方

```powershell
python -m jarvis
```

```
あなた> 今日は何曜日？
  … get_current_time を使用中

ジャービス> 今日は月曜日です。
```

`/reset` で会話をリセット、`/exit` で終了します。

### 設定（`.env`）

| 変数 | 既定値 | 説明 |
|---|---|---|
| `ANTHROPIC_API_KEY` | （必須） | Claude API キー |
| `JARVIS_MODEL` | `claude-opus-5-5` | 使うモデル |
| `JARVIS_EFFORT` | `medium` | 考える深さ。`low` にすると速く安く、`high` 以上で丁寧に |
| `JARVIS_USER_NAME` | なし | 呼びかけに使う名前 |

## ツールの追加方法

`jarvis/tools/` にファイルを作り、関数に `@registry.tool(...)` を付けて、`jarvis/tools/__init__.py` でインポートします。

```python
from .registry import registry

@registry.tool(
    name="open_notepad",
    description="メモ帳を開きます。",
)
def open_notepad() -> str:
    import subprocess
    subprocess.Popen(["notepad.exe"])
    return "メモ帳を開きました"
```

削除や上書きなど取り返しのつかない操作には `dangerous=True` を付けてください。実行前に必ず `[y/N]` で確認されます。

## テスト

```powershell
pip install -r requirements-dev.txt
pytest
```

テストは API を呼ばないので、キーがなくても実行できます。
