//go:build windows

package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"syscall"
	"unsafe"
)

var (
	user32   = syscall.NewLazyDLL("user32.dll")
	shell32  = syscall.NewLazyDLL("shell32.dll")
	ole32    = syscall.NewLazyDLL("ole32.dll")
	kernel32 = syscall.NewLazyDLL("kernel32.dll")

	procRegisterClassExW = user32.NewProc("RegisterClassExW")
	procCreateWindowExW  = user32.NewProc("CreateWindowExW")
	procDefWindowProcW   = user32.NewProc("DefWindowProcW")
	procShowWindow       = user32.NewProc("ShowWindow")
	procUpdateWindow     = user32.NewProc("UpdateWindow")
	procGetMessageW      = user32.NewProc("GetMessageW")
	procTranslateMessage = user32.NewProc("TranslateMessage")
	procDispatchMessageW = user32.NewProc("DispatchMessageW")
	procPostQuitMessage  = user32.NewProc("PostQuitMessage")
	procMessageBoxW      = user32.NewProc("MessageBoxW")
	procLoadCursorW      = user32.NewProc("LoadCursorW")
	procSendMessageW     = user32.NewProc("SendMessageW")
	procGetWindowTextW   = user32.NewProc("GetWindowTextW")
	procSetWindowTextW   = user32.NewProc("SetWindowTextW")
	procEnableWindow     = user32.NewProc("EnableWindow")

	procGetModuleHandleW = kernel32.NewProc("GetModuleHandleW")
	procGetStockObject   = syscall.NewLazyDLL("gdi32.dll").NewProc("GetStockObject")

	procSHBrowseForFolderW  = shell32.NewProc("SHBrowseForFolderW")
	procSHGetPathFromIDList = shell32.NewProc("SHGetPathFromIDListW")
	procCoTaskMemFree       = ole32.NewProc("CoTaskMemFree")
	procCoInitializeEx      = ole32.NewProc("CoInitializeEx")
	procCoUninitialize      = ole32.NewProc("CoUninitialize")
)

const (
	WS_OVERLAPPED            = 0x00000000
	WS_CAPTION               = 0x00C00000
	WS_SYSMENU               = 0x00080000
	WS_MINIMIZEBOX           = 0x00020000
	WS_VISIBLE               = 0x10000000
	WS_CHILD                 = 0x40000000
	WS_TABSTOP               = 0x00010000
	WS_BORDER                = 0x00800000
	ES_AUTOHSCROLL           = 0x0080
	BS_PUSHBUTTON            = 0x00000000
	BS_AUTORADIOBUTTON       = 0x00000009
	BS_DEFPUSHBUTTON         = 0x00000001
	BS_GROUPBOX              = 0x00000007
	SS_LEFT                  = 0x00000000
	SS_CENTER                = 0x00000001
	COLOR_WINDOW             = 5
	IDC_ARROW                = 32512
	WM_DESTROY               = 0x0002
	WM_COMMAND               = 0x0111
	WM_SETFONT               = 0x0030
	BM_SETCHECK              = 0x00F1
	BM_GETCHECK              = 0x00F0
	BST_CHECKED              = 1
	SW_SHOW                  = 5
	MB_OK                    = 0x00000000
	MB_ICONINFORMATION       = 0x00000040
	MB_ICONERROR             = 0x00000010
	MB_ICONWARNING           = 0x00000030
	BIF_RETURNONLYFSDIRS     = 0x00000001
	BIF_NEWDIALOGSTYLE       = 0x00000040
	DEFAULT_GUI_FONT         = 17
	COINIT_APARTMENTTHREADED = 0x2
)

const (
	idPathEdit = 1001
	idBrowse   = 1002
	idLow      = 2001
	idMedium   = 2002
	idHigh     = 2003
	idSave     = 3001
)

type WNDCLASSEX struct {
	cbSize        uint32
	style         uint32
	lpfnWndProc   uintptr
	cbClsExtra    int32
	cbWndExtra    int32
	hInstance     syscall.Handle
	hIcon         syscall.Handle
	hCursor       syscall.Handle
	hbrBackground syscall.Handle
	lpszMenuName  *uint16
	lpszClassName *uint16
	hIconSm       syscall.Handle
}

type MSG struct {
	HWnd    syscall.Handle
	Message uint32
	WParam  uintptr
	LParam  uintptr
	Time    uint32
	Pt      struct{ X, Y int32 }
}

type BrowseInfo struct {
	hwndOwner      syscall.Handle
	pidlRoot       uintptr
	pszDisplayName *uint16
	lpszTitle      *uint16
	ulFlags        uint32
	lpfn           uintptr
	lParam         uintptr
	iImage         int32
}

type Config struct {
	SchemaVersion int    `json:"schema_version"`
	AuditLevel    string `json:"audit_level"`
}

var (
	hMain, hPathEdit, hLow, hMedium, hHigh, hDesc, hSave syscall.Handle
	hFont                                                syscall.Handle
	wndProcCallback                                      uintptr
	classNamePtr                                         *uint16
)

func ptr(s string) *uint16 { p, _ := syscall.UTF16PtrFromString(s); return p }

func loWord(v uintptr) uint16 { return uint16(v & 0xffff) }

func createControl(class, text string, style uint32, x, y, w, h int32, parent syscall.Handle, id uintptr) syscall.Handle {
	hwnd, _, _ := procCreateWindowExW.Call(
		0,
		uintptr(unsafe.Pointer(ptr(class))),
		uintptr(unsafe.Pointer(ptr(text))),
		uintptr(style),
		uintptr(x), uintptr(y), uintptr(w), uintptr(h),
		uintptr(parent), id, 0, 0,
	)
	if hwnd != 0 && hFont != 0 {
		procSendMessageW.Call(hwnd, WM_SETFONT, uintptr(hFont), 1)
	}
	return syscall.Handle(hwnd)
}

func getText(hwnd syscall.Handle) string {
	buf := make([]uint16, 4096)
	n, _, _ := procGetWindowTextW.Call(uintptr(hwnd), uintptr(unsafe.Pointer(&buf[0])), uintptr(len(buf)))
	return syscall.UTF16ToString(buf[:n])
}

func setText(hwnd syscall.Handle, s string) {
	procSetWindowTextW.Call(uintptr(hwnd), uintptr(unsafe.Pointer(ptr(s))))
}

func message(title, text string, flags uintptr) {
	procMessageBoxW.Call(uintptr(hMain), uintptr(unsafe.Pointer(ptr(text))), uintptr(unsafe.Pointer(ptr(title))), flags)
}

func levelDescription(level string) string {
	switch level {
	case "low":
		return "快速 LOW：保留事实与引用底线。全审高风险论断和具体数字；中低风险只处理关键命中。适合普通作业或赶时间。"
	case "high":
		return "深度 HIGH：系统核验高/中风险论断、重要引用簇、摘要—正文—结论一致性，并对关键结论做更深入证据复核。不会无脑重读全部论文。"
	default:
		return "标准 MEDIUM（推荐）：全审高风险，处理主要中风险、重要引用簇、核心跨章节一致性与结构型 AI 味；质量与 token 消耗平衡。"
	}
}

func currentLevel() string {
	r, _, _ := procSendMessageW.Call(uintptr(hHigh), BM_GETCHECK, 0, 0)
	if r == BST_CHECKED {
		return "high"
	}
	r, _, _ = procSendMessageW.Call(uintptr(hLow), BM_GETCHECK, 0, 0)
	if r == BST_CHECKED {
		return "low"
	}
	return "medium"
}

func selectLevel(level string) {
	vals := map[syscall.Handle]uintptr{hLow: 0, hMedium: 0, hHigh: 0}
	switch strings.ToLower(level) {
	case "low":
		vals[hLow] = BST_CHECKED
	case "high":
		vals[hHigh] = BST_CHECKED
	default:
		vals[hMedium] = BST_CHECKED
		level = "medium"
	}
	for h, v := range vals {
		procSendMessageW.Call(uintptr(h), BM_SETCHECK, v, 0)
	}
	setText(hDesc, levelDescription(level))
}

func configPath(project string) string {
	return filepath.Join(project, "assignment", "workflow-config.json")
}

func loadConfig(project string) {
	selectLevel("medium")
	b, err := os.ReadFile(configPath(project))
	if err != nil {
		return
	}
	var m map[string]any
	if json.Unmarshal(b, &m) != nil {
		return
	}
	if v, ok := m["audit_level"].(string); ok {
		selectLevel(v)
	}
}

func saveConfig() {
	project := strings.TrimSpace(getText(hPathEdit))
	if project == "" {
		message("无法保存", "请先选择课程论文项目文件夹。", MB_OK|MB_ICONWARNING)
		return
	}
	st, err := os.Stat(project)
	if err != nil || !st.IsDir() {
		message("项目路径无效", "所选路径不是可访问的文件夹：\n\n"+project, MB_OK|MB_ICONERROR)
		return
	}
	assignment := filepath.Join(project, "assignment")
	if err := os.MkdirAll(assignment, 0755); err != nil {
		message("创建目录失败", err.Error(), MB_OK|MB_ICONERROR)
		return
	}
	path := configPath(project)
	m := map[string]any{}
	if b, err := os.ReadFile(path); err == nil {
		_ = json.Unmarshal(b, &m) // Preserve future/unknown fields when possible.
	}
	m["schema_version"] = 1
	m["audit_level"] = currentLevel()
	out, _ := json.MarshalIndent(m, "", "  ")
	out = append(out, '\n')
	if err := os.WriteFile(path, out, 0644); err != nil {
		message("保存失败", err.Error(), MB_OK|MB_ICONERROR)
		return
	}
	message("已保存", fmt.Sprintf("审计档位：%s\n\n配置已写入：\n%s\n\nAdaptive Evidence Budget 仍由 Skill 自动执行，不设置固定全文篇数上限。", strings.ToUpper(currentLevel()), path), MB_OK|MB_ICONINFORMATION)
}

func browseFolder() {
	display := make([]uint16, 260)
	bi := BrowseInfo{
		hwndOwner:      hMain,
		pszDisplayName: &display[0],
		lpszTitle:      ptr("选择课程论文项目根目录（其中将创建/读取 assignment 文件夹）"),
		ulFlags:        BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE,
	}
	pidl, _, _ := procSHBrowseForFolderW.Call(uintptr(unsafe.Pointer(&bi)))
	if pidl == 0 {
		return
	}
	defer procCoTaskMemFree.Call(pidl)
	pathBuf := make([]uint16, 32768)
	ok, _, _ := procSHGetPathFromIDList.Call(pidl, uintptr(unsafe.Pointer(&pathBuf[0])))
	if ok == 0 {
		return
	}
	path := syscall.UTF16ToString(pathBuf)
	if path != "" {
		setText(hPathEdit, path)
		loadConfig(path)
	}
}

func wndProc(hwnd syscall.Handle, msg uint32, wParam, lParam uintptr) uintptr {
	switch msg {
	case WM_COMMAND:
		switch loWord(wParam) {
		case idBrowse:
			browseFolder()
			return 0
		case idLow:
			selectLevel("low")
			return 0
		case idMedium:
			selectLevel("medium")
			return 0
		case idHigh:
			selectLevel("high")
			return 0
		case idSave:
			saveConfig()
			return 0
		}
	case WM_DESTROY:
		procPostQuitMessage.Call(0)
		return 0
	}
	r, _, _ := procDefWindowProcW.Call(uintptr(hwnd), uintptr(msg), wParam, lParam)
	return r
}

func main() {
	// Win32 windows and their message queues are bound to the creating OS thread.
	// Keep the GUI goroutine on one thread for the entire lifetime of the app.
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()

	procCoInitializeEx.Call(0, COINIT_APARTMENTTHREADED)
	defer procCoUninitialize.Call()

	hInst, _, _ := procGetModuleHandleW.Call(0)
	font, _, _ := procGetStockObject.Call(DEFAULT_GUI_FONT)
	hFont = syscall.Handle(font)
	cursor, _, _ := procLoadCursorW.Call(0, IDC_ARROW)

	classNamePtr = ptr("CNKIAuditSettingsWindowStable")
	wndProcCallback = syscall.NewCallback(wndProc)
	wc := WNDCLASSEX{
		cbSize:        uint32(unsafe.Sizeof(WNDCLASSEX{})),
		lpfnWndProc:   wndProcCallback,
		hInstance:     syscall.Handle(hInst),
		hCursor:       syscall.Handle(cursor),
		hbrBackground: syscall.Handle(COLOR_WINDOW + 1),
		lpszClassName: classNamePtr,
	}
	if r, _, _ := procRegisterClassExW.Call(uintptr(unsafe.Pointer(&wc))); r == 0 {
		message("启动失败", "无法注册窗口类。", MB_OK|MB_ICONERROR)
		return
	}

	style := uint32(WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX)
	hwnd, _, _ := procCreateWindowExW.Call(
		0,
		uintptr(unsafe.Pointer(classNamePtr)),
		uintptr(unsafe.Pointer(ptr("CNKI 论文设置 · 审计档位（稳定版）"))),
		uintptr(style),
		0x80000000, 0x80000000, 650, 465,
		0, 0, hInst, 0,
	)
	if hwnd == 0 {
		return
	}
	hMain = syscall.Handle(hwnd)

	createControl("STATIC", "课程论文项目", WS_CHILD|WS_VISIBLE|SS_LEFT, 24, 22, 180, 24, hMain, 0)
	hPathEdit = createControl("EDIT", "", WS_CHILD|WS_VISIBLE|WS_BORDER|WS_TABSTOP|ES_AUTOHSCROLL, 24, 50, 490, 28, hMain, idPathEdit)
	createControl("BUTTON", "浏览…", WS_CHILD|WS_VISIBLE|WS_TABSTOP|BS_PUSHBUTTON, 525, 49, 92, 30, hMain, idBrowse)

	createControl("BUTTON", "审计强度", WS_CHILD|WS_VISIBLE|BS_GROUPBOX, 24, 95, 593, 205, hMain, 0)
	hLow = createControl("BUTTON", "快速  LOW", WS_CHILD|WS_VISIBLE|WS_TABSTOP|BS_AUTORADIOBUTTON, 47, 126, 150, 30, hMain, idLow)
	hMedium = createControl("BUTTON", "标准  MEDIUM（推荐）", WS_CHILD|WS_VISIBLE|WS_TABSTOP|BS_AUTORADIOBUTTON, 47, 161, 220, 30, hMain, idMedium)
	hHigh = createControl("BUTTON", "深度  HIGH", WS_CHILD|WS_VISIBLE|WS_TABSTOP|BS_AUTORADIOBUTTON, 47, 196, 150, 30, hMain, idHigh)
	hDesc = createControl("STATIC", "", WS_CHILD|WS_VISIBLE|SS_LEFT, 47, 238, 535, 50, hMain, 0)

	createControl("STATIC", "说明：此工具不访问 CNKI、不启动 Agent、不写论文；只修改当前项目的 assignment\\workflow-config.json。\r\nAdaptive Evidence Budget 始终按 evidence gap 工作，不设置固定全文篇数上限。", WS_CHILD|WS_VISIBLE|SS_LEFT, 24, 318, 593, 50, hMain, 0)
	hSave = createControl("BUTTON", "保存到项目", WS_CHILD|WS_VISIBLE|WS_TABSTOP|BS_DEFPUSHBUTTON, 465, 382, 152, 36, hMain, idSave)

	project := ""
	if len(os.Args) > 1 {
		if st, err := os.Stat(os.Args[1]); err == nil && st.IsDir() {
			project = os.Args[1]
		}
	}
	if project == "" {
		project, _ = os.Getwd()
	}
	setText(hPathEdit, project)
	loadConfig(project)

	procShowWindow.Call(hwnd, SW_SHOW)
	procUpdateWindow.Call(hwnd)

	var msg MSG
	for {
		r, _, _ := procGetMessageW.Call(uintptr(unsafe.Pointer(&msg)), 0, 0, 0)
		if int32(r) <= 0 {
			break
		}
		procTranslateMessage.Call(uintptr(unsafe.Pointer(&msg)))
		procDispatchMessageW.Call(uintptr(unsafe.Pointer(&msg)))
	}
}
