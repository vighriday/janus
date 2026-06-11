// JANUS — Azure infrastructure for `azd up`.
//
// Provisions the runtime (a Container Apps environment hosting the API and the
// console, a user-assigned managed identity, a registry, Key Vault, and
// Application Insights) and grants the identity keyless data-plane access to the
// pre-existing AI services (Search / OpenAI / Content Safety / Storage), which
// are passed in as parameters. No keys anywhere — the apps authenticate with the
// managed identity via DefaultAzureCredential.

targetScope = 'resourceGroup'

@minLength(1)
@maxLength(64)
@description('Name of the azd environment; tags every resource.')
param environmentName string

@minLength(1)
@description('Azure region for the new resources.')
param location string = resourceGroup().location

@description('Object id of the deploying user (azd injects AZURE_PRINCIPAL_ID). Optional.')
param principalId string = ''

// --- Existing AI services (endpoints + resource ids passed via azd env) -------
param searchEndpoint string
param searchResourceId string
param searchKnowledgeBase string = 'janus-decisions-kb'
param searchKnowledgeSource string = 'janus-decisions-ks'
param openAiEndpoint string
param openAiResourceId string
param contentSafetyEndpoint string
param contentSafetyResourceId string
param storageAccountResourceId string = ''

var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }
var prefix = 'janus'

// --- Monitoring ---------------------------------------------------------------
resource law 'Microsoft.OperationalInsights/workspaces@2025-02-01' = {
  name: '${prefix}-law-${resourceToken}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${prefix}-appi-${resourceToken}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: law.id
  }
}

// --- Identity -----------------------------------------------------------------
resource uami 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-id-${resourceToken}'
  location: location
  tags: tags
}

// --- Key Vault (RBAC mode; holds the App Insights connection string) ----------
resource keyVault 'Microsoft.KeyVault/vaults@2024-11-01' = {
  name: 'kv${resourceToken}'
  location: location
  tags: tags
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
  }
}

// --- Container registry (azd pushes the built images here) --------------------
resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: 'acr${resourceToken}'
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, uami.id, acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// --- Key Vault Secrets User for the identity ----------------------------------
var kvSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'
resource kvSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, uami.id, kvSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// --- Container Apps environment -----------------------------------------------
resource cae 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${prefix}-cae-${resourceToken}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: law.properties.customerId
        sharedKey: law.listKeys().primarySharedKey
      }
    }
  }
}

// --- Data-plane role assignments on the existing AI services ------------------
module roles 'roles.bicep' = {
  name: 'janus-roles'
  params: {
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
    searchResourceId: searchResourceId
    openAiResourceId: openAiResourceId
    contentSafetyResourceId: contentSafetyResourceId
    storageAccountResourceId: storageAccountResourceId
  }
}

// Grant the deploying user the same read roles, so the app can be exercised
// locally with `az login` right after `azd up` — fully keyless on both sides.
module devRoles 'roles.bicep' = if (!empty(principalId)) {
  name: 'janus-dev-roles'
  params: {
    principalId: principalId
    principalType: 'User'
    searchResourceId: searchResourceId
    openAiResourceId: openAiResourceId
    contentSafetyResourceId: contentSafetyResourceId
    storageAccountResourceId: storageAccountResourceId
  }
}

// --- The two services ---------------------------------------------------------
var apiName = '${prefix}-api-${resourceToken}'
var consoleName = '${prefix}-console-${resourceToken}'

module api 'app.bicep' = {
  name: 'janus-api'
  params: {
    name: apiName
    serviceName: 'api'
    location: location
    tags: tags
    environmentId: cae.id
    uamiId: uami.id
    acrLoginServer: acr.properties.loginServer
    targetPort: 8000
    envVars: [
      { name: 'AZURE_CLIENT_ID', value: uami.properties.clientId }
      { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
      { name: 'AZURE_SEARCH_ENDPOINT', value: searchEndpoint }
      { name: 'AZURE_SEARCH_KNOWLEDGE_BASE', value: searchKnowledgeBase }
      { name: 'AZURE_SEARCH_KNOWLEDGE_SOURCE', value: searchKnowledgeSource }
      { name: 'AZURE_OPENAI_ENDPOINT', value: openAiEndpoint }
      { name: 'AZURE_CONTENT_SAFETY_ENDPOINT', value: contentSafetyEndpoint }
    ]
  }
}

module console 'app.bicep' = {
  name: 'janus-console'
  params: {
    name: consoleName
    serviceName: 'web'
    location: location
    tags: tags
    environmentId: cae.id
    uamiId: uami.id
    acrLoginServer: acr.properties.loginServer
    targetPort: 3100
    envVars: [
      { name: 'NEXT_PUBLIC_API_BASE_URL', value: 'https://${apiName}.${cae.properties.defaultDomain}' }
    ]
  }
}

output AZURE_CONTAINER_REGISTRY_ENDPOINT string = acr.properties.loginServer
output APPLICATIONINSIGHTS_CONNECTION_STRING string = appInsights.properties.ConnectionString
output AZURE_KEY_VAULT_URI string = keyVault.properties.vaultUri
output API_URI string = 'https://${api.outputs.fqdn}'
output CONSOLE_URI string = 'https://${console.outputs.fqdn}'
