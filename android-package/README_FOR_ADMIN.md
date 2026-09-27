# Stratos_squirrel_vs_viper: Google Play package

Everything needed to build the Android app and publish it on the Stratos Games Play Console,
the same way BLOXPLODE is built (Capacitor wrapping a web build).

```
android-package/
  www/                       the game (web build): index.html + stratos_squirrel_vs_viper.apk/.tar.gz
  capacitor.config.json      appId com.stratosgames.squirrelvsviper, appName Stratos_squirrel_vs_viper
  package.json               Capacitor 7 dependencies
  store-listing/
    STORE_LISTING.md         title, descriptions, category, data-safety and content-rating answers
    graphics/                icon 512, feature graphic 1024x500, 5 screenshots 1280x720
```

The same game is live on the web at https://saiqulmodi.github.io/Stratos_squirrel_vs_viper/ (open it on a phone to try the touch controls).

## Before you start

- Node.js 20+, JDK 21, Android Studio (the same setup used for BLOXPLODE).
- The Stratos Games **upload key** (keystore) used for BLOXPLODE / Arrow Rush.
- If your BLOXPLODE project uses a different Capacitor version, change `^7.0.0` in `package.json` to that version.

## 1. Create the Android project

```bash
cd android-package
npm install
npx cap add android
npx cap sync android
```

## 2. Landscape + full screen

Open `android/app/src/main/AndroidManifest.xml` and add these to the `<activity ... android:name=".MainActivity"` tag:

```xml
android:screenOrientation="sensorLandscape"
android:resizeableActivity="false"
```

The game is a 1280x720 landscape game and resizes itself to fit the screen.

Optional, to hide the status bar for a true full-screen look: in `android/app/src/main/res/values/styles.xml`,
set the `AppTheme.NoActionBar` parent to `Theme.AppCompat.DayNight.NoActionBar` and add:

```xml
<item name="android:windowFullscreen">true</item>
```

## 3. App icon

In Android Studio: right-click `app` > New > Image Asset > Launcher Icons, choose
`store-listing/graphics/icon_512.png`, set the background colour to `#090C16`, then Finish.

## 4. Version

`android/app/build.gradle`: `versionCode 1`, `versionName "1.0"` (increase `versionCode` for every upload).

## 5. Test on a real phone (the Stratos human play-test gate)

`npx cap open android`, then Run on a connected phone. Check:
1. **Internet on:** it loads, shows "Ready to start", tap once, and the start screen appears.
2. **Tap to start:** drag the left side to move, hold FIRE to shoot, tap NOVA, tap LV 20.
3. **Sound:** attack sounds play (only attacks make sound; MUTE button next to the level bar).
4. **Full screen:** rotating the phone keeps it in landscape, and the whole screen fits (power panels visible top-left and top-right).

Note: the game engine is downloaded from `pygame-web.github.io` when the app starts, so **the phone needs internet**.
The first start takes 10-20 seconds; after that it's cached.

## 6. Build the release file

Android Studio > Build > Generate Signed Bundle / APK > **Android App Bundle** > use the Stratos upload key > `release`.
The file is `android/app/release/app-release.aab`.

## 7. Play Console

1. Create app: name `Stratos_squirrel_vs_viper`, Game, Free.
2. Fill in **App content** and **Main store listing** from `store-listing/STORE_LISTING.md` and upload the files in `store-listing/graphics/`.
3. Testing > Internal testing: upload `app-release.aab`, test on a phone, then promote to Production and send for review.

## Updating the game later

When the game changes, the new web build is published to GitHub Pages automatically by us. To update the app, copy the new
`index.html`, `stratos_squirrel_vs_viper.apk` and `stratos_squirrel_vs_viper.tar.gz` from
https://github.com/saiqulmodi/Stratos_squirrel_vs_viper/tree/main/docs into `www/`, then `npx cap sync android`,
bump `versionCode`, rebuild the bundle and upload.

Questions: Saiqul (the game source is at https://github.com/saiqulmodi/Stratos_squirrel_vs_viper).
