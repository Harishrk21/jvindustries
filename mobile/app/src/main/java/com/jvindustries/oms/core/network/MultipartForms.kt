package com.jvindustries.oms.core.network

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File

fun textPart(value: String): RequestBody =
    value.toRequestBody("text/plain".toMediaType())

fun imagePart(file: File, name: String = "image"): MultipartBody.Part {
    val body = file.asRequestBody("image/jpeg".toMediaType())
    return MultipartBody.Part.createFormData(name, file.name, body)
}
