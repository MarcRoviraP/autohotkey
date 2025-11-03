#NoEnv
#SingleInstance Force
#Persistent

; Atajo para mostrar/ocultar VLC
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
 

    Loop, %vlcWindows%
    {
        vlcID := vlcWindows%A_Index%
        
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
        
        ; Ocultar nuevamente
        ;WinHide, ahk_id %vlcID%
        
        if (cleanTitle != "" && cleanTitle != "VLC" && cleanTitle != "VLC media player")
        {
            foundTitle := cleanTitle
            break
        }
    }
    
    return foundTitle
}

CleanVLCTitle(title)
{
    ; Primero intentar con regex para casos específicos de VLC
    clean := RegExReplace(title, "i)\s*-\s*(VLC|Reproductor multimedia VLC|VLC media player).*$", "")
    
    ; Si no cambió, usar el método de split
    if (clean = title && InStr(title, " - "))
    {
        parts := StrSplit(title, " - ")
        if (parts.Length() > 1)
        {
            ; Unir todas excepto la última
            clean := parts[1]
            Loop, % parts.Length() - 1
            {
                if (A_Index > 1)
                    clean .= " - " . parts[A_Index]
            }
        }
    }
    
    clean := Trim(clean)
    clean := StrReplace(clean, ".mp3", " ")
    if (IsOnlyVLC(clean) || StrLen(clean) < 2)
        return ""
        
    return clean
}

IsOnlyVLC(text)
{
    text := Trim(text)
    vlcPatterns := ["VLC", "Reproductor multimedia", "Media Player", "Multimedia Player"]
    
    For index, pattern in vlcPatterns
    {
        if (RegExMatch(text, "i)^\s*" . pattern . "\s*$"))
            return true
    }
    
    return false
}

ShowCustomTooltip(text)
{
    SetTimer, CloseSongTooltip, Off
    Gui, SongTooltip:Destroy
    Gui, SongTooltipBorder:Destroy

    ; --- CONFIGURACIÓN ---
    bgColor := "101010"         ; Fondo del tooltip
    borderColor := "404040"     ; Color del borde
    fontColor := "F3F3F3"       ; Color del texto
    fontName := "Calibri"
    fontSize := 10
    padding := 5               ; Espaciado interno uniforme
    maxWidth := 1920             ; Ancho máximo más razonable
    borderWidth := 1            ; Grosor del borde
    ; ----------------------

    ; Crear GUI temporal para medir texto
    Gui, SongTooltipTemp:New, +ToolWindow
    Gui, SongTooltipTemp:Font, s%fontSize% Bold, %fontName%
    Gui, SongTooltipTemp:Add, Text, R1, %text%
    GuiControlGet, textSize, SongTooltipTemp:Pos, Static1
    Gui, SongTooltipTemp:Destroy

    ; Calcular dimensiones del tooltip
    width := textSizeW + (padding * 2)
    height := textSizeH + (padding * 2)
    
    ; Aplicar límites
    if (width > maxWidth)
        width := maxWidth
        ; Versión simplificada para esquina inferior derecha
    WinGetPos, , , , taskbarHeight, ahk_class Shell_TrayWnd
    posX := A_ScreenWidth - width - 1
    posY := A_ScreenHeight - height - taskbarHeight

    ; Calcular posiciones del borde
    borderX := posX - borderWidth
    borderY := posY - borderWidth
    borderW := width + (borderWidth * 2)
    borderH := height + (borderWidth * 2)

    ; --- GUI del borde ---
    Gui, SongTooltipBorder:New, -Caption +ToolWindow +AlwaysOnTop +E0x20
    Gui, SongTooltipBorder:Color, %borderColor%
    Gui, SongTooltipBorder:Show, x%borderX% y%borderY% w%borderW% h%borderH% NoActivate

    ; --- GUI del contenido ---
    Gui, SongTooltip:New, -Caption +ToolWindow +AlwaysOnTop +E0x20
    Gui, SongTooltip:Color, %bgColor%
    Gui, SongTooltip:Font, s%fontSize% c%fontColor% Bold, %fontName%
    
    ; Calcular área de texto con padding
    textWidth := width - (padding * 2)
    textHeight := height - (padding * 2)
    
    ; Agregar texto centrado con padding uniforme
    Gui, SongTooltip:Add, Text, x%padding% y%padding% w%textWidth% h%textHeight% Center, %text%
    Gui, SongTooltip:Show, x%posX% y%posY% w%width% h%height% NoActivate, SongTooltipWindow

    ; Cerrar automáticamente
    SetTimer, CloseSongTooltip, 5000
}

CloseSongTooltip:
    Gui, SongTooltip:Destroy
    Gui, SongTooltipBorder:Destroy
    SetTimer, CloseSongTooltip, Off
return

!Numpad0::
    ShowSongTooltip()
return

^!x::ExitApp