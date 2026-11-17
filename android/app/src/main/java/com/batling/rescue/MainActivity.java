package com.batling.rescue;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/**
 * BATling Rescue para Android: abre la versión web del juego (la misma de GitHub Pages, hecha con pygbag)
 * a pantalla completa, en horizontal y sin barra del navegador. Los controles táctiles son los del juego.
 * Necesita internet para cargar el juego; si no hay conexión muestra una pantalla para reintentar.
 */
public class MainActivity extends Activity {

    /** Dirección del juego publicado. Si cambia la página, solo hay que cambiar esta línea. */
    static final String GAME_URL = "https://elizabeth-alva.github.io/Batling-Rescue/";

    private WebView web;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Window w = getWindow();
        w.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);          // la pantalla no se apaga jugando
        if (Build.VERSION.SDK_INT >= 28) {                                    // también debajo de la cámara (notch)
            w.getAttributes().layoutInDisplayCutoutMode =
                    WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
        }

        web = new WebView(this);
        web.setBackgroundColor(Color.BLACK);
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);                    // pygbag (Python en WebAssembly) necesita JavaScript
        s.setDomStorageEnabled(true);                    // los récords se guardan en el localStorage
        s.setMediaPlaybackRequiresUserGesture(false);    // la música y los sonidos suenan sin pedir permiso
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(true);
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);

        web.setWebChromeClient(new WebChromeClient());
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri url = request.getUrl();
                Uri game = Uri.parse(GAME_URL);
                if ("file".equals(url.getScheme()) || game.getHost().equals(url.getHost())) {
                    return false;                        // el juego se queda dentro de la app
                }
                startActivity(new Intent(Intent.ACTION_VIEW, url));    // otros enlaces: en el navegador
                return true;
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {          // sin internet: pantalla para reintentar
                    view.loadUrl("file:///android_asset/offline.html");
                }
            }
        });

        if (savedInstanceState != null) {
            web.restoreState(savedInstanceState);
        } else {
            web.loadUrl(GAME_URL);
        }
        hideSystemBars();
    }

    /** Pantalla completa: esconde la barra de estado y los botones de navegación (se ven deslizando el dedo). */
    private void hideSystemBars() {
        if (Build.VERSION.SDK_INT >= 30) {
            getWindow().setDecorFitsSystemWindows(false);
            WindowInsetsController c = getWindow().getInsetsController();
            if (c != null) {
                c.hide(WindowInsets.Type.systemBars());
                c.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
            }
        } else {
            getWindow().getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                    | View.SYSTEM_UI_FLAG_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                    | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                    | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
        }
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            hideSystemBars();
        }
    }

    /** Botón «atrás» del teléfono: pregunta antes de cerrar el juego (para no salir por accidente). */
    @Override
    public void onBackPressed() {
        new AlertDialog.Builder(this)
                .setTitle(R.string.exit_title)
                .setPositiveButton(R.string.exit_yes, (d, which) -> finish())
                .setNegativeButton(R.string.exit_no, null)
                .show();
    }

    @Override
    protected void onPause() {                           // al salir de la app el juego se detiene (y su sonido)
        super.onPause();
        web.onPause();
        web.pauseTimers();
    }

    @Override
    protected void onResume() {
        super.onResume();
        web.onResume();
        web.resumeTimers();
        hideSystemBars();
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        web.saveState(outState);
    }

    @Override
    protected void onDestroy() {
        web.destroy();
        super.onDestroy();
    }
}
