#NoEnv
#SingleInstance Force
#Persistent

; Timer para ocultar VLC cuando se abra
SetTimer, CheckAndHideVLC, 1000
return

CheckAndHideVLC:
    Process, Exist, vlc.exe
    vlcPID := ErrorLevel
    
    if (vlcPID > 0)
    {
        WinGet, vlcWindows, List, ahk_exe vlc.exe
        Loop, %vlcWindows%
        {
            vlcID := vlcWindows%A_Index%
            
            ; Ocultar completamente la ventana
            WinHide, ahk_id %vlcID%
            
            ; Quitar de la barra de tareas y área de notificaciones
            WinSet, Style, -0x10000000, ahk_id %vlcID%  ; Quitar WS_VISIBLE
            WinSet, ExStyle, -0x40000, ahk_id %vlcID%   ; Quitar WS_EX_APPWINDOW (evita botón en barra de tareas)
            WinSet, ExStyle, +0x80, ahk_id %vlcID%      ; Agregar WS_EX_TOOLWINDOW (oculta de barra de tareas)
            WinSet, ExStyle, +0x8000000, ahk_id %vlcID% ; Agregar WS_EX_NOACTIVATE (no se activa al pasar mouse)
            
            ; Forzar a que no sea una ventana de primer plano
            DllCall("SetWindowPos", "uint", vlcID, "uint", 0
                , "int", 0, "int", 0, "int", 0, "int", 0
                , "uint", 0x0083)  ; SWP_NOACTIVATE | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER
        }
        SetTimer, CheckAndHideVLC, Off
    }
return

^!v::
    Process, Exist, vlc.exe
    vlcPID := ErrorLevel
    
    if (vlcPID > 0)
    {
        ; Buscar la ventana principal de VLC
        WinGet, vlcWindows, List, ahk_exe vlc.exe
        vlcID := ""
        
        ; Encontrar la ventana principal (normalmente la primera)
        Loop, %vlcWindows%
        {
            currentID := vlcWindows%A_Index%
            WinGetTitle, currentTitle, ahk_id %currentID%
            
            ; Si es la ventana principal o tiene un título que no sea vacío
            if (currentTitle != "" && currentTitle != "VLC media player")
            {
                vlcID := currentID
                break
            }
        }
        
        ; Si no encontramos una ventana específica, usar la primera
        if (vlcID = "")
            vlcID := vlcWindows1
        
        if (vlcID != "")
        {
            WinGet, IsVisible, Style, ahk_id %vlcID%
            
            if (IsVisible & 0x10000000) ; Si está visible
            {
                ; Ocultar completamente
                WinHide, ahk_id %vlcID%
                WinSet, Style, -0x10000000, ahk_id %vlcID%
                WinSet, ExStyle, -0x40000, ahk_id %vlcID%
                WinSet, ExStyle, +0x80, ahk_id %vlcID%
                WinSet, ExStyle, +0x8000000, ahk_id %vlcID%
            }
            else
            {
                ; Mostrar y restaurar estilos normales
                WinSet, Style, +0x10000000, ahk_id %vlcID% ; WS_VISIBLE
                WinSet, ExStyle, -0x80, ahk_id %vlcID%     ; Quitar WS_EX_TOOLWINDOW
                WinSet, ExStyle, +0x40000, ahk_id %vlcID%  ; Agregar WS_EX_APPWINDOW (para barra de tareas)
                WinSet, ExStyle, -0x8000000, ahk_id %vlcID%; Quitar WS_EX_NOACTIVATE
                WinShow, ahk_id %vlcID%
                WinActivate, ahk_id %vlcID%
                WinRestore, ahk_id %vlcID%
            }
        }
    }
    else
    {
        MsgBox, VLC no está en ejecución.
    }
return

ShowSongTooltip()
{
    Process, Exist, vlc.exe
    vlcPID := ErrorLevel
    
    if (vlcPID > 0)
    {
        ; Obtener el nombre usando método que funciona en segundo plano
        songName := GetVLCInfoBackground()
        
        if (songName = "")
            songName := "VLC en ejecución (sin medios activos)"
    }
    else
    {
        songName := "VLC no está en ejecución"
    }
    
    ; Mostrar tooltip
    ShowCustomTooltip(songName)
}

GetVLCInfoBackground()
{
    ; Método 1: Hacer visible momentáneamente
    tempTitle := GetTitleByTemporaryShow()
    if (tempTitle != "")
        return tempTitle
    
    ; Método 2: Verificar si hay audio activo (indicando reproducción)
    if (IsVLCAudioPlaying())
    {
        return "VLC reproduciendo contenido (audio activo)"
    }
    
    return "VLC en ejecución (en pausa o sin audio)"
}

IsVLCAudioPlaying()
{
    ; Esta es una aproximación - podrías usar herramientas externas
    ; como AudioRouter o analizar el mezclador de audio de Windows
    ; Por ahora, devolvemos true asumiendo que si VLC está ejecutándose, está reproduciendo
    return true
}

GetTitleByTemporaryShow()
{
    ; Hacer visible VLC momentáneamente para leer el título
    WinGet, vlcWindows, List, ahk_exe vlc.exe
    foundTitle := ""
    
    Loop, %vlcWindows%
    {
        vlcID := vlcWindows%A_Index%
        
        ; Guardar el estado actual
        WinGet, savedStyle, Style, ahk_id %vlcID%
        WinGet, savedExStyle, ExStyle, ahk_id %vlcID%
        
        ; Hacer visible momentáneamente (muy rápido)
        WinSet, Style, +0x10000000, ahk_id %vlcID%  ; WS_VISIBLE
        WinSet, ExStyle, -0x80, ahk_id %vlcID%      ; Quitar WS_EX_TOOLWINDOW
        WinSet, ExStyle, +0x40000, ahk_id %vlcID%   ; Agregar WS_EX_APPWINDOW
        WinShow, ahk_id %vlcID%
        
        ; Pequeña pausa para que se actualice
        Sleep, 10
        
        ; Leer el título
        WinGetTitle, currentTitle, ahk_id %vlcID%
        cleanTitle := CleanVLCTitle(currentTitle)
        
        ; Restaurar estado oculto inmediatamente
        WinHide, ahk_id %vlcID%
        WinSet, Style, %savedStyle%, ahk_id %vlcID%
        WinSet, ExStyle, %savedExStyle%, ahk_id %vlcID%
        
        if (cleanTitle != "" && cleanTitle != "VLC" && cleanTitle != "VLC media player")
        {
            foundTitle := cleanTitle
            break
        }
    }
    
    return foundTitle
}

GetTitleFromHiddenWindows()
{
    ; Intentar leer el título de ventanas ocultas (puede no funcionar)
    WinGet, windowList, List, ahk_exe vlc.exe
    
    Loop, %windowList%
    {
        windowID := windowList%A_Index%
        WinGetTitle, windowTitle, ahk_id %windowID%
        
        cleanTitle := CleanVLCTitle(windowTitle)
        if (cleanTitle != "" && cleanTitle != "VLC" && cleanTitle != "VLC media player")
        {
            return cleanTitle
        }
    }
    return ""
}

CleanVLCTitle(title)
{
    ; Limpiar el título para obtener solo el nombre del archivo/media
    clean := title
    
    ; Remover sufijos comunes de VLC
    clean := RegExReplace(clean, "i)\s*-\s*VLC\s*media\s*player\s*$", "")
    clean := RegExReplace(clean, "i)\s*-\s*VLC\s*$", "")
    clean := RegExReplace(clean, "i)\s*\[Playing\]\s*$", "")
    clean := RegExReplace(clean, "i)\s*\[\s*\d+%?\s*\]\s*$", "")
    
    ; Remover información de tiempo (00:00:00)
    clean := RegExReplace(clean, "\s*\d{1,2}:\d{2}:\d{2}\s*$", "")
    clean := RegExReplace(clean, "\s*\d{1,2}:\d{2}\s*$", "")
    
    ; Limpiar espacios y guiones sobrantes
    clean := Trim(clean, " -[]")
    
    ; Si después de limpiar queda muy corto o es solo "VLC", considerar vacío
    if (StrLen(clean) < 3 || clean = "VLC" || clean = "VLC media player")
        return ""
    
    return clean
}

ShowCustomTooltip(text)
{
    ; Cerrar tooltip anterior si existe
    SetTimer, CloseSongTooltip, Off
    Gui, SongTooltip:Destroy
    
    ; Crear tooltip personalizado
    Gui, SongTooltip:-Caption +ToolWindow +AlwaysOnTop
    Gui, SongTooltip:Color, 000000
    Gui, SongTooltip:Font, cF3F3F3 s10, Segoe UI
    
    ; Calcular posición y dimensiones
    width := 400  ; Más ancho para nombres largos
    height := 80
    posX := A_ScreenWidth - width - 20
    posY := A_ScreenHeight - height - 20
    
    textWidth := width - 20
    textHeight := height - 20
    
    Gui, SongTooltip:Add, Text, x10 y10 w%textWidth% h%textHeight% Center, %text%
    Gui, SongTooltip:Show, x%posX% y%posY% w%width% h%height%, SongTooltipWindow
    
    SetTimer, CloseSongTooltip, 3000
}

!Numpad0::
    ShowSongTooltip()
return

CloseSongTooltip:
    SetTimer, CloseSongTooltip, Off
    Gui, SongTooltip:Destroy
return

^!x::ExitApp