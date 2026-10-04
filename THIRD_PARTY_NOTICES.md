# Third-Party Notices / 第三者ソフトウェアの表示

File Organizer v3.2.0 (Windows 配布版) には、以下の第三者ソフトウェアが含まれています。
各ソフトウェアには、それぞれのライセンスが適用されます（File Organizer の利用条件より優先します）。
ライセンス全文は `THIRD_PARTY_LICENSES` フォルダに、配布元のファイルを改変せずに収録しています。

File Organizer v3.2.0 (Windows distribution) includes the third-party software listed below.
Each component is licensed under its own terms, reproduced unmodified in the `THIRD_PARTY_LICENSES` folder.

| Component | Version | License | Copyright notice | License text |
| --- | --- | --- | --- | --- |
| Python (runtime, standard library) | 3.14.7 | PSF License Agreement (and the licenses of incorporated software) | Copyright © 2001 Python Software Foundation. Copyright © 2000 BeOpen.com. Copyright © 1995-2001 CNRI. Copyright © 1991-1995 SMC. | `Python-LICENSE.txt`, `Python-Incorporated-Software.txt` |
| OpenSSL (libssl-3.dll, libcrypto-3.dll; shipped with Python) | 3.5.7 | Apache License 2.0 | Copyright 1998-2026 The OpenSSL Authors. All rights reserved. | Apache License 2.0 text in `Python-LICENSE.txt` |
| libffi (libffi-8.dll; shipped with Python) | — | MIT | Copyright (c) 1996-2022 Anthony Green, Red Hat, Inc and others. | `Python-LICENSE.txt` |
| bzip2, Zstandard (shipped with Python) | 1.0.8 / — | bzip2 license / BSD | See license text | `Python-LICENSE.txt` |
| SQLite (sqlite3.dll; shipped with Python) | 3.50.4 | Public domain | — | — |
| Other code incorporated in Python (expat, libmpdec, zlib, mimalloc, etc.) | — | Various (see text) | See license text | `Python-Incorporated-Software.txt` |
| Microsoft Visual C++ Runtime (VCRUNTIME140.dll, VCRUNTIME140_1.dll) | 14.51.36247.0 | Microsoft Distributable Code (see "Additional Conditions for this Windows binary build") | © Microsoft Corporation. All rights reserved. | `Python-LICENSE.txt` |
| Flask | 3.1.3 | BSD-3-Clause | Copyright 2010 Pallets | `Flask-LICENSE.txt` |
| Werkzeug | 3.1.8 | BSD-3-Clause | Copyright 2007 Pallets | `Werkzeug-LICENSE.txt` |
| Jinja2 | 3.1.6 | BSD-3-Clause | Copyright 2007 Pallets | `Jinja2-LICENSE.txt` |
| MarkupSafe | 3.0.3 | BSD-3-Clause | Copyright 2010 Pallets | `MarkupSafe-LICENSE.txt` |
| itsdangerous | 2.2.0 | BSD-3-Clause | Copyright 2011 Pallets | `itsdangerous-LICENSE.txt` |
| click | 8.5.0 | BSD-3-Clause | Copyright 2014 Pallets | `click-LICENSE.txt` |
| blinker | 1.9.0 | MIT | Copyright 2010 Jason Kirtland | `blinker-LICENSE.txt` |
| colorama | 0.4.6 | BSD-3-Clause | Copyright (c) 2010 Jonathan Hartley | `colorama-LICENSE.txt` |
| typing_extensions | 4.16.0 | PSF-2.0 | See license text | `typing_extensions-LICENSE.txt` |
| pywebview (incl. WebBrowserInterop DLLs and pywebview-android.jar shipped in the package) | 6.2.1 | BSD-3-Clause | Copyright (c) 2014-2017, Roman Sirokov | `pywebview-LICENSE.txt` |
| bottle | 0.13.4 | MIT | Copyright (c) 2009-2024, Marcel Hellkamp. | `bottle-LICENSE.txt` |
| proxy_tools | 0.1.0 | MIT (package metadata); the source file states "BSD, see LICENSE" | :copyright: (c) 2013 by Armin Ronacher (adapted by Jonathan Tushman 2014). | No license file is distributed with the package (see note below) |
| Python.NET (pythonnet, Python.Runtime.dll) | 3.2.0 | MIT | Copyright (c) 2006-2021 the contributors of the Python.NET project | `pythonnet-LICENSE.txt`, `pythonnet-AUTHORS.md` |
| clr-loader (ClrLoader.dll) | 0.3.1 | MIT | Copyright (c) 2019-2026 Benedikt Reinartz | `clr_loader-LICENSE.txt` |
| cffi | 2.1.1 | MIT-0 (see text) | See license text | `cffi-LICENSE.txt` |
| pycparser | 3.0 | BSD-3-Clause | Copyright (c) 2008-2022, Eli Bendersky | `pycparser-LICENSE.txt` |
| Microsoft Edge WebView2 SDK (Microsoft.Web.WebView2.Core.dll, Microsoft.Web.WebView2.WinForms.dll, WebView2Loader.dll) | 1.0.3856.49 | Microsoft WebView2 SDK license (BSD-style) and third-party notices | Copyright (C) Microsoft Corporation. All rights reserved. | `Microsoft.Web.WebView2-LICENSE.txt`, `Microsoft.Web.WebView2-NOTICE.txt` |
| PyInstaller bootloader, loader modules and run-time hooks (embedded in File Organizer.exe) | 6.22.3 | Bootloader / loader: GPL-2.0-or-later with the Bootloader Exception. Run-time hooks: Apache License 2.0 | Copyright (c) 2010-2023, PyInstaller Development Team; Copyright (c) 2005-2009, Giovanni Bajo | `PyInstaller-COPYING.txt` (Apache License 2.0 text in `Python-LICENSE.txt`) |

## Notes / 補足

- **PyInstaller**: File Organizer.exe embeds only the PyInstaller bootloader, its loader modules and run-time hooks, which are covered by the Bootloader Exception and the Apache License 2.0 as stated in `PyInstaller-COPYING.txt`. The PyInstaller build tool itself is not included in the distribution.
- **Microsoft Edge WebView2 Runtime** is not included; it is a separate Microsoft component installed on Windows and is governed by Microsoft's own terms.
- **proxy_tools**: the published package declares the MIT license in its metadata but ships no license file, and its source file header reads: "Proxy. Extracted from Werkzeug / :copyright: (c) 2013 by Armin Ronacher (adapted by Jonathan Tushman 2014). / :license: BSD, see LICENSE for more details." The copyright notice is reproduced here as published. Werkzeug's BSD-3-Clause license text is in `Werkzeug-LICENSE.txt`.
- `Python-Incorporated-Software.txt` is the "Licenses and Acknowledgements for Incorporated Software" section of the official Python 3.14 documentation (`Doc/html/license.html` of the installed Python), converted from HTML to plain text without changing its wording. Python's documentation notes that this list is incomplete.
