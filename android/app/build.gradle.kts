plugins {
    id("com.android.application")
}

android {
    namespace = "com.batling.rescue"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.batling.rescue"
        minSdk = 24                 // Android 7.0 o más nuevo
        targetSdk = 35
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
}
