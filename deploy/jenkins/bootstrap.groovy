import jenkins.model.Jenkins
import jenkins.model.JenkinsLocationConfiguration
import hudson.security.HudsonPrivateSecurityRealm
import hudson.security.FullControlOnceLoggedInAuthorizationStrategy
import hudson.model.Node
import hudson.model.BooleanParameterDefinition
import hudson.model.ParametersDefinitionProperty
import hudson.slaves.DumbSlave
import hudson.slaves.JNLPLauncher
import hudson.slaves.RetentionStrategy
import hudson.plugins.git.GitSCM
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition
import com.cloudbees.plugins.credentials.CredentialsScope
import com.cloudbees.plugins.credentials.SystemCredentialsProvider
import com.cloudbees.plugins.credentials.domains.Domain
import com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey

def instance = Jenkins.get()
instance.setNumExecutors(0)
if (!(instance.securityRealm instanceof HudsonPrivateSecurityRealm)) {
    def realm = new HudsonPrivateSecurityRealm(false)
    realm.createAccount('jaime', new File('/run/secrets/jenkins_password').text.trim())
    instance.setSecurityRealm(realm)
    def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
    strategy.setAllowAnonymousRead(false)
    instance.setAuthorizationStrategy(strategy)
}
JenkinsLocationConfiguration.get().setUrl(System.getenv('JENKINS_PUBLIC_URL'))
if (instance.getNode('photohearth-ci') == null) {
    def agent = new DumbSlave('photohearth-ci', '/home/jenkins/agent', new JNLPLauncher())
    agent.setNumExecutors(1)
    agent.setLabelString('photohearth-ci')
    agent.setMode(Node.Mode.EXCLUSIVE)
    agent.setRetentionStrategy(new RetentionStrategy.Always())
    instance.addNode(agent)
}
def secret = new File('/agent-config/secret')
secret.text = instance.getComputer('photohearth-ci').getJnlpMac()
secret.setReadable(false, false)
secret.setReadable(true, true)
secret.setWritable(false, false)
secret.setWritable(true, true)
if (instance.getItem('PhotoHearth') == null) {
    def job = instance.createProject(WorkflowJob, 'PhotoHearth')
    def scm = new GitSCM('https://github.com/JaimeOnaindia/PhotoHearth.git')
    scm.branches = [new hudson.plugins.git.BranchSpec('*/main')]
    job.setDefinition(new CpsScmFlowDefinition(scm, 'Jenkinsfile'))
    job.save()
}
if (instance.getItem('PhotoHearth Deploy') == null) {
    def job = instance.createProject(WorkflowJob, 'PhotoHearth Deploy')
    def scm = new GitSCM('https://github.com/JaimeOnaindia/PhotoHearth.git')
    scm.branches = [new hudson.plugins.git.BranchSpec('*/main')]
    job.setDefinition(new CpsScmFlowDefinition(scm, 'Jenkinsfile.deploy'))
    job.setDescription('Despliegue manual del artefacto aprobado por PhotoHearth CI.')
    job.save()
}
def deployJob = instance.getItem('PhotoHearth Deploy')
if (deployJob.getProperty(ParametersDefinitionProperty) == null) {
    deployJob.addProperty(new ParametersDefinitionProperty(
        new BooleanParameterDefinition('DRY_RUN', false, 'Comprobar sin actualizar producción')
    ))
}
def deployKey = new File('/run/secrets/deploy_key')
def credentials = SystemCredentialsProvider.getInstance()
if (!credentials.getCredentials().any { it.id == 'photohearth-deploy' }) {
    def key = new BasicSSHUserPrivateKey(
        CredentialsScope.GLOBAL,
        'photohearth-deploy',
        'james',
        new BasicSSHUserPrivateKey.DirectEntryPrivateKeySource(deployKey.getText('UTF-8')),
        '',
        'Acceso limitado al despliegue de PhotoHearth'
    )
    credentials.getStore().addCredentials(Domain.global(), key)
}
instance.save()
