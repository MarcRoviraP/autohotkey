#SingleInstance, [force|ignore|prompt|off]
; === VLC Playlist Simple (TEST) ===
F2::
    GetVLCPlaylistSimple()
return

GetVLCPlaylistSimple() {
    try {
        http := ComObjCreate("WinHttp.WinHttpRequest.5.1")
        http.Open("GET", "http://localhost:8080/requests/playlist.json", false)
        http.SetRequestHeader("Authorization", "Basic " . Base64Encode(":password"))
        http.Send()
        
        if (http.Status = 200) {
            ; Guardar respuesta cruda para analizar
            FileDelete, vlc_response.json
            FileAppend, % http.ResponseText, vlc_response.json
            MsgBox, Éxito! Respuesta guardada en vlc_response.json
        } else {
            MsgBox, Error
        }
    } catch e {
        MsgBox, Error: %e%
    }
}

Base64Encode(string) {
    VarSetCapacity(bin, StrPut(string, "UTF-8")) 
    len := StrPut(string, &bin, "UTF-8") - 1 
    DllCall("crypt32\CryptBinaryToString", "ptr", &bin, "uint", len, "uint", 0x1, "ptr", 0, "uint*", size)
    VarSetCapacity(buf, size << 1, 0)
    DllCall("crypt32\CryptBinaryToString", "ptr", &bin, "uint", len, "uint", 0x1, "ptr", &buf, "uint*", size)
    return StrGet(&buf)
}