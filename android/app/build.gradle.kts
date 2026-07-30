plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.hypragent"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.hypragent"
        minSdk = 30
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")

    // WebSocket client
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    // JSON serialization
    implementation("org.json:json:20240303")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    // Lifecycle
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.2")

    // ML Kit text recognition (OCR fallback)
    implementation("com.google.mlkit:text-recognition:16.0.1")
}
