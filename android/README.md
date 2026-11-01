# Find Imob para Android

Este módulo transforma o painel Streamlit existente em um aplicativo Android instalável que abre a interface web responsiva do Find Imob. O servidor continua sendo executado no backend; o app Android não empacota os coletores Python.

## Requisitos para compilar

- Android Studio (ou Android SDK + Gradle)
- JDK 17
- Um servidor Find Imob acessível publicamente por HTTPS com certificado válido

O app deliberadamente recusa HTTP e certificados inválidos. `findimob.local`, o IP privado da rede e o certificado CA local não são adequados para um lançamento na Play Store.

## Configurar e compilar

Abra a pasta `android/` no Android Studio e sincronize o Gradle. Para compilar pela linha de comando, com Android SDK e Gradle instalados:

```bash
gradle :app:assembleDebug -PAPP_BASE_URL=https://app.seu-dominio.com
```

Para gerar o Android App Bundle de lançamento:

```bash
gradle :app:bundleRelease -PAPP_BASE_URL=https://app.seu-dominio.com
```

O bundle é produzido em `app/build/outputs/bundle/release/app-release.aab`. Configure uma chave de assinatura de release no Android Studio/Gradle antes do envio. Nunca inclua a chave de assinatura no Git.

## Antes de enviar à Play Store

1. Publique o backend Find Imob em um domínio HTTPS público, estável e monitorado.
2. Configure login, domínio permitido e callback Google OAuth para o domínio público. Login Google não pode ser testado usando `.local`.
3. Defina a URL de produção via `-PAPP_BASE_URL` e configure a assinatura segura do bundle.
4. Prepare política de privacidade, formulário Data safety, classificação etária, ícones promocionais e capturas de tela conforme os dados efetivamente tratados.
5. Teste o fluxo completo em dispositivos Android e no canal de teste interno da Play Console antes de pedir publicação.

Este repositório não contém credenciais de produção, domínio público, chave de assinatura nem conta Play Console; portanto, ainda não existe um AAB pronto para publicação.
