// Keyless data-plane access for the managed identity, granted on the existing AI
// services. These are the only roles JANUS needs at runtime:
//   - Search Index Data Reader  → Foundry IQ agentic retrieve (knowledge base)
//   - Cognitive Services OpenAI User → lesson/levers + embeddings
//   - Cognitive Services User   → Content Safety groundedness + prompt shields
//   - Storage Blob Data Reader  → the corpus blob source (when provisioned)

param principalId string
@allowed(['ServicePrincipal', 'User'])
param principalType string = 'ServicePrincipal'
param searchResourceId string
param openAiResourceId string
param contentSafetyResourceId string
param storageAccountResourceId string = ''

var searchIndexDataReader = '1407120a-92aa-4202-b7e9-c0e197c71c8f'
var openAiUser = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
var cognitiveServicesUser = 'a97b65f3-24c7-4388-baec-2e87135dc908'
var storageBlobDataReader = '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'

resource search 'Microsoft.Search/searchServices@2024-06-01-preview' existing = {
  name: last(split(searchResourceId, '/'))
}
resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: last(split(openAiResourceId, '/'))
}
resource safety 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: last(split(contentSafetyResourceId, '/'))
}

resource searchRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, principalId, searchIndexDataReader)
  scope: search
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataReader)
    principalId: principalId
    principalType: principalType
  }
}

resource openAiRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openai.id, principalId, openAiUser)
  scope: openai
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAiUser)
    principalId: principalId
    principalType: principalType
  }
}

resource safetyRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(safety.id, principalId, cognitiveServicesUser)
  scope: safety
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUser)
    principalId: principalId
    principalType: principalType
  }
}

// Storage is optional — only when the corpus blob account id is supplied.
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = if (!empty(storageAccountResourceId)) {
  name: empty(storageAccountResourceId) ? 'placeholder' : last(split(storageAccountResourceId, '/'))
}

resource storageRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(storageAccountResourceId)) {
  name: guid(storageAccountResourceId, principalId, storageBlobDataReader)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataReader)
    principalId: principalId
    principalType: principalType
  }
}
