// One JANUS service as a Container App. Reused for the API and the console.
// The image is a placeholder at provision time; `azd deploy` pushes the real
// image and updates the app, matched by the azd-service-name tag.

param name string
@description('Must match the service key in azure.yaml (api | console).')
param serviceName string
param location string
param tags object
param environmentId string
param uamiId string
param acrLoginServer string
param targetPort int
param envVars array = []

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: union(tags, { 'azd-service-name': serviceName })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${uamiId}': {}
    }
  }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: targetPort
        transport: 'auto'
      }
      registries: [
        {
          server: acrLoginServer
          identity: uamiId
        }
      ]
    }
    template: {
      containers: [
        {
          name: serviceName
          // Placeholder; azd replaces this with the built image on deploy.
          image: 'mcr.microsoft.com/k8se/quickstart:latest'
          resources: {
            cpu: json('0.5')
            memory: '1.0Gi'
          }
          env: envVars
        }
      ]
      // min 1 so the in-memory workflow survives the approval round-trip and a
      // cold start never fronts the demo.
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

output fqdn string = app.properties.configuration.ingress.fqdn
output name string = app.name
