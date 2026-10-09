# 每轮发布约定

用户已确认后续研究更新统一发布到 https://github.com/ChenKaichen-SCUT/Flowevo-Bot 的 main 分支。
双连字符地址 ChenKaichen--SCUT 不使用。本地发布检出位于 `/mnt/Space1/Flowevo-Bot-upload`。

每轮先完成代码、验证、真实实验记录和报告，再同步安全的整个工作目录、提交并推送，核对远端提交。
保留历史数据和原始评分；上传源码、数据集、逐请求安全日志和报告。
不上传 miyao.txt、API 密钥、环境变量文件、虚拟环境、缓存及嵌套 Git 内部文件。
上传前扫描凭据及压缩包内容，并更新 UPLOAD_MANIFEST.json 和 UPLOAD_EXCLUSIONS.json。

同步与扫描脚本为 `Flowevo-Bot/scripts/publish_workspace.py`（只复制、扫描和生成清单，不自动提交）。
在发布检出中检查状态后 `git add -f -- .`、提交并 `git push origin main`，随后核对远端 HEAD。
