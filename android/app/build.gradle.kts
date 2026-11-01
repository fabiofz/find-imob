plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val configuredBaseUrl = providers.gradleProperty("APP_BASE_URL")
    .orElse("")
    .get()

android {
    namespace = "br.com.findimob"
    compileSdk = 35

    defaultConfig {
        applicationId = "br.com.findimob"
        minSdk = 23
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"
        buildConfigField("String", "APP_BASE_URL", "\"$configuredBaseUrl\"")
    }

    buildFeatures {
        buildConfig = true
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
    implementation("androidx.core:core-ktx:1.15.0")
}
