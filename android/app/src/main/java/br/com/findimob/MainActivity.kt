package br.com.findimob

import android.annotation.SuppressLint
import android.app.Activity
import android.graphics.Color
import android.content.Intent
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.webkit.CookieManager
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.core.view.WindowCompat
import java.net.URI

class MainActivity : Activity() {
    private lateinit var webView: WebView
    private lateinit var progress: ProgressBar
    private lateinit var errorPanel: LinearLayout

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, true)
        window.statusBarColor = Color.rgb(18, 18, 18)
        window.navigationBarColor = Color.BLACK
        buildLayout()

        val startUrl = BuildConfig.APP_BASE_URL.trim()
        if (!isSecureHttpUrl(startUrl)) {
            showSetupMessage()
            return
        }

        CookieManager.getInstance().setAcceptCookie(true)
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true)
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.databaseEnabled = true
        webView.settings.loadsImagesAutomatically = true
        webView.settings.useWideViewPort = true
        webView.settings.loadWithOverviewMode = true
        webView.settings.javaScriptCanOpenWindowsAutomatically = false
        webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                progress.progress = newProgress
                progress.visibility = if (newProgress in 1..99) View.VISIBLE else View.GONE
            }
        }
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val url = request.url.toString()
                if (!isSecureHttpUrl(url)) {
                    Toast.makeText(this@MainActivity, "Link bloqueado por segurança.", Toast.LENGTH_SHORT).show()
                    return true
                }
                val host = request.url.host
                val appHost = URI(startUrl).host
                if (host != appHost) {
                    startActivity(Intent(Intent.ACTION_VIEW, request.url))
                    return true
                }
                return false
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: android.webkit.WebResourceError?
            ) {
                if (request?.isForMainFrame == true) {
                    webView.visibility = View.GONE
                    errorPanel.visibility = View.VISIBLE
                }
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                errorPanel.visibility = View.GONE
                webView.visibility = View.VISIBLE
            }
        }
        webView.loadUrl(startUrl)
    }

    private fun buildLayout() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(18, 18, 18))
        }
        progress = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 100
            progressTintList = android.content.res.ColorStateList.valueOf(Color.rgb(48, 201, 130))
            visibility = View.GONE
        }
        webView = WebView(this)
        errorPanel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(32, 32, 32, 32)
            visibility = View.GONE
        }
        val errorText = TextView(this).apply {
            text = "Não foi possível conectar ao Find Imob. Verifique sua internet e tente novamente."
            textSize = 18f
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
        }
        val retry = Button(this).apply {
            text = "Tentar novamente"
            setOnClickListener {
                errorPanel.visibility = View.GONE
                webView.visibility = View.VISIBLE
                webView.reload()
            }
        }
        errorPanel.addView(errorText)
        errorPanel.addView(retry)
        root.addView(progress, LinearLayout.LayoutParams(-1, 3))
        root.addView(webView, LinearLayout.LayoutParams(-1, 0, 1f))
        root.addView(errorPanel, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)
    }

    private fun showSetupMessage() {
        webView.visibility = View.GONE
        errorPanel.visibility = View.VISIBLE
        errorPanel.removeAllViews()
        val text = TextView(this).apply {
            text = "O app Android ainda não foi ligado ao servidor público do Find Imob. Configure APP_BASE_URL com o endereço HTTPS de produção e gere novamente o pacote."
            textSize = 18f
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
        }
        errorPanel.addView(text)
    }

    private fun isSecureHttpUrl(value: String): Boolean = try {
        val uri = URI(value)
        uri.scheme == "https" && !uri.host.isNullOrBlank()
    } catch (_: Exception) {
        false
    }

    override fun onBackPressed() {
        if (::webView.isInitialized && webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }

    override fun onDestroy() {
        if (::webView.isInitialized) {
            webView.stopLoading()
            webView.destroy()
        }
        super.onDestroy()
    }
}
