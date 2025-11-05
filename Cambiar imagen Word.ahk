#NoEnv
#SingleInstance Force
SetTitleMatchMode, 2

; --- Solo cuando Word esté activo ---
#IfWinActive ahk_exe WINWORD.EXE

<+.::               ; Shift IZQ + "." (tecla principal)
    ; SoundBeep, 900, 100  ; <- descomenta para oír confirmación al pulsar
    Gosub, __REEMPLAZAR
return

; Fallbacks por si tu "." usa otro scancode o el numpad:
<+sc034::           ; muchos teclados ES mapean "." a sc034
    Gosub, __REEMPLAZAR
return

<+NumpadDot::       ; punto del teclado numérico
    Gosub, __REEMPLAZAR
return

#IfWinActive

; ====== LÓGICA DE REEMPLAZO MEJORADA ======
__REEMPLAZAR:
    ; --- Conectar con Word de manera más robusta ---
    word := ""
    try {
        word := ComObjActive("Word.Application")
    } catch e {
        try {
            word := ComObjGet("Word.Application")
        } catch e2 {
            MsgBox, 48, Error, No se pudo conectar con Word.`nAsegúrate de que Word esté abierto y una imagen seleccionada.
            return
        }
    }

    if (!word) {
        MsgBox, 48, Error, No se pudo acceder a Word.
        return
    }

    ; Desactivar actualización de pantalla para evitar parpadeos
    word.ScreenUpdating := False

    ; Pequeña pausa para estabilizar
    Sleep, 100

    ; --- Verificar selección de manera más robusta ---
    sel := word.Selection
    if (!sel) {
        word.ScreenUpdating := True
        MsgBox, 48, Aviso, No hay selección activa en Word.`nSelecciona una imagen primero.
        return
    }

    ; Verificar que realmente hay algo seleccionado y es una imagen
    hasInlineShape := false
    hasShape := false
    
    try {
        hasInlineShape := (sel.InlineShapes.Count > 0)
    } catch {
        hasInlineShape := false
    }
    
    try {
        hasShape := (sel.ShapeRange.Count > 0)
    } catch {
        hasShape := false
    }

    if (!hasInlineShape && !hasShape) {
        word.ScreenUpdating := True
        
        ; Intentar método alternativo: buscar imágenes en el rango de selección
        try {
            ; Verificar si hay imágenes cerca del punto de inserción
            range := sel.Range
            if (range.InlineShapes.Count > 0) {
                ; Seleccionar la primera imagen inline en el rango
                range.InlineShapes(1).Select
                sel := word.Selection
                hasInlineShape := true
            } else if (range.Parent.Shapes.Count > 0) {
                ; Buscar formas cerca de la selección (método aproximado)
                MsgBox, 48, Aviso, Se detectaron formas en el documento pero no seleccionadas.`nPor favor selecciona manualmente la imagen.
                word.ScreenUpdating := True
                return
            } else {
                MsgBox, 48, Aviso, No se detectó ninguna imagen en la selección actual.`n`nPor favor:`n1. Haz clic directamente sobre la imagen`n2. Asegúrate de que la imagen tenga bordes de selección`n3. Intenta nuevamente
            }
        } catch {
            MsgBox, 48, Aviso, No se detectó ninguna imagen seleccionada.`nSelecciona una imagen haciendo clic directamente sobre ella.
        }
        return
    }

    ; --- Abrir selector en el Escritorio ---
    startDir := A_Desktop  ; Esto apunta directamente al escritorio del usuario
    FileSelectFile, ruta, , %startDir%, Elige la imagen para reemplazar, Imágenes (*.jpg; *.jpeg; *.png; *.gif; *.bmp; *.tif; *.tiff; *.webp)
    if (ruta = "") {
        word.ScreenUpdating := True
        return
    }

    ; Verificar que el archivo existe
    IfNotExist, %ruta%
    {
        word.ScreenUpdating := True
        MsgBox, 48, Error, El archivo seleccionado no existe.
        return
    }

    ; --- Caso 1: imagen en línea con el texto ---
 if (hasInlineShape) {
    try {
        ils := sel.InlineShapes(1)
        w := ils.Width
        h := ils.Height
        rng := ils.Range.Duplicate

        ; Guardar formato completo
        ils.Range.ShapeRange(1).PickUp()

        ; Insertar nueva imagen
        nuevo := rng.InlineShapes.AddPicture(ruta, false, true)
        nuevo.LockAspectRatio := -1
        nuevo.Width := w
        nuevo.Height := h

        ; Aplicar formato completo
        nuevo.Range.ShapeRange(1).Apply()

        ; Eliminar original
        ils.Delete
    } catch e {
        word.ScreenUpdating := True
        MsgBox, 48, Error, Error al reemplazar imagen en línea: %e%
        return
    }
    word.ScreenUpdating := True
    return
}

    ; --- Caso 2: imagen flotante (con ajuste de texto) ---
if (hasShape) {
    try {
        shp := sel.ShapeRange(1)
        shp.PickUp()  ; Copiar formato completo

        ; Crear nueva imagen
        newShp := shp.Anchor.InlineShapes.AddPicture(ruta, false, true).ConvertToShape
        newShp.LockAspectRatio := -1
        newShp.Width := shp.Width
        newShp.Height := shp.Height
        newShp.Left := shp.Left
        newShp.Top := shp.Top
        newShp.RelativeHorizontalPosition := shp.RelativeHorizontalPosition
        newShp.RelativeVerticalPosition := shp.RelativeVerticalPosition
        newShp.WrapFormat.Type := shp.WrapFormat.Type
        newShp.WrapFormat.Side := shp.WrapFormat.Side

        ; Aplicar formato completo
        newShp.Apply()

        ; Eliminar original
        shp.Delete
    } catch e {
        word.ScreenUpdating := True
        MsgBox, 48, Error, Error al reemplazar imagen flotante: %e%
        return
    }
    word.ScreenUpdating := True
    return
}

    word.ScreenUpdating := True
return