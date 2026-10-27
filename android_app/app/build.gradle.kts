plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
if (file("google-services.json").exists()) apply(plugin = "com.google.gms.google-services")
android {
    buildFeatures { buildConfig = true }
    namespace = "org.sfa.aire"
    compileSdk = 35
    defaultConfig {
        applicationId = "org.sfa.aire"
        minSdk = 26
        targetSdk = 35
        testInstrumentationRunner = "org.sfa.aire.SessionVaultInstrumentation"
        versionCode = 13
        versionName = "0.7.4"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}
dependencies {
    implementation(platform("com.google.firebase:firebase-bom:33.7.0"))
    implementation("com.google.firebase:firebase-messaging")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
}
